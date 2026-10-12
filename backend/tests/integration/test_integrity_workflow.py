"""Integrity checks end to end (spec 006, AC-006-7…12): a statement edited in a PDF editor comes out
TAMPERED with the expected findings at the edited row; the bank's original comes out CLEAN."""

import io
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from app.adapters.cloud_tasks import InlineTaskQueue
from app.adapters.page_renderer import DefaultPageRenderer
from app.adapters.policy_files import load_plans
from app.adapters.spreadsheet_reader import DefaultSpreadsheetReader
from app.core.settings import Settings
from app.domain.models.workspace import Subscription
from app.domain.reading import (
    StatementHeader,
    StatementPageReading,
    StatementRowReading,
    StatementTotals,
)
from app.main import AppDeps, create_app
from tests.fakes.clock import FixedClock
from tests.fakes.document_reader import FakeDocumentReader
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.document_storage import FakeDocumentStorage
from tests.fakes.identity_admin import FakeIdentityAdmin
from tests.fakes.month_repository import FakeMonthRepository
from tests.fakes.run_repository import FakeRunRepository
from tests.fakes.usage_repository import FakeUsageRepository
from tests.fakes.workspace_repository import FakeWorkspaceRepository
from tests.integration.test_documents_api import PLANS_FILE
from tests.unit.test_auth import FakeTokenVerifier

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "statements"
AUTH = {"Authorization": "Bearer owner"}


def _printed(value: str | None) -> str | None:
    return None if value is None else f"{Decimal(value):,.2f}"


def _reader(truth: dict) -> FakeDocumentReader:
    """Recorded from the truth, as printed: an edited value is read as the edit shows it."""
    edits = {(e["rowIndex"], e["field"]): e["after"] for e in truth.get("tampering", [])}

    def page(no: int) -> StatementPageReading:
        rows = []
        for i, r in enumerate(truth["rows"], start=1):
            if r["page"] != no:
                continue
            value = {f: _printed(edits.get((i, f), r[f])) for f in ("debit", "credit", "balance")}
            rows.append(
                StatementRowReading(
                    row_on_page=len(rows) + 1,
                    date_text=f"{date.fromisoformat(r['date']):%d/%m/%Y}",
                    description=r["description"],
                    debit_text=value["debit"],
                    credit_text=value["credit"],
                    balance_text=value["balance"],
                )
            )
        if no == 1:
            opening = StatementRowReading(
                row_on_page=0,
                date_text="01/03/2026",
                description="OPENING BALANCE",
                balance_text=_printed(truth["opening"]),
            )
            header = StatementHeader(
                bank_name="Archipelago Commerce Bank",
                account_holder=truth["holder"],
                account_number=truth["accountNumber"],
                currency="IDR",
                period_start_text="01 Mar 2026",
                period_end_text="31 Mar 2026",
            )
            return StatementPageReading(page=1, header=header, rows=[opening, *rows])
        totals = StatementTotals(closing_balance_text=_printed(truth["closing"]))
        return StatementPageReading(page=no, rows=rows, totals=totals)

    return FakeDocumentReader(pages=page)


async def _run(name: str) -> tuple[dict, list[dict], dict]:
    truth = json.loads((FIXTURES / f"{name}.truth.json").read_text())
    workspaces = FakeWorkspaceRepository()
    usage = FakeUsageRepository(workspaces=workspaces)
    usage.subscriptions["org_1"] = Subscription(
        plan_id="free_trial", status="TRIALING", trial_ends_at=datetime(2026, 10, 25, tzinfo=UTC)
    )
    settings = Settings(app_role="all", task_queue_mode="inline", month_run_delay_seconds=0)  # type: ignore[arg-type]
    deps = AppDeps(
        settings,
        load_plans(PLANS_FILE),
        workspace_repo=workspaces,
        usage_repo=usage,
        identity=FakeIdentityAdmin(),
        run_repo=FakeRunRepository(),
        month_repo=FakeMonthRepository(),
        doc_repo=FakeDocumentRepository(),
        storage=FakeDocumentStorage(),
        renderer=DefaultPageRenderer(),
        spreadsheet_reader=DefaultSpreadsheetReader(),
        clock=FixedClock(datetime(2026, 4, 5, tzinfo=UTC)),
        reader=_reader(truth),
        token_verifier=FakeTokenVerifier(
            {"owner": {"uid": "u-1", "orgId": "org_1", "role": "owner"}}
        ),
    )
    app = create_app(settings, deps=deps)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        pdf = (FIXTURES / f"{name}.pdf").read_bytes()
        res = await client.post(
            "/api/documents",
            headers=AUTH,
            files={"file": (f"{name}.pdf", io.BytesIO(pdf), "application/pdf")},
        )
        assert res.status_code == 201, res.text
        queue = deps.task_queue
        assert isinstance(queue, InlineTaskQueue)
        await queue.drain()
        doc_id = res.json()["docId"]
        doc = (await client.get(f"/api/documents/{doc_id}", headers=AUTH)).json()
        findings = (
            await client.get("/api/findings", params={"docId": doc_id}, headers=AUTH)
        ).json()
    return doc, findings["items"], truth


async def test_a_statement_edited_in_a_pdf_editor_is_tampered():
    doc, findings, truth = await _run("acb-2026-03-edited")
    assert doc["status"] == "DONE", doc.get("statusDetail")
    assert doc["integrity"]["verdict"] == "TAMPERED"
    codes = {f["code"] for f in findings}
    assert set(truth["expected"]["findingsP0"]) <= codes, codes
    [a01] = [f for f in findings if f["code"] == "A01_RUNNING_BALANCE_BREAK"]
    assert a01["severity"] == "CRITICAL"
    assert a01["facts"]["row"] == "12"  # the edited row: opening balance is row 1
    assert a01["facts"]["difference"] == "-6000000.00"
    assert a01["facts"]["continuesFromPrinted"] == "yes"
    assert a01["evidence"][1]["bbox"] is not None and a01["nextSteps"]
    [m04] = [f for f in findings if f["code"] == "M04_FONT_ANOMALY_IN_VALUES"]
    assert m04["facts"]["value"] == "7,250,000.00"
    assert {f["code"]: f["severity"] for f in findings}["M03_MULTIPLE_REVISIONS"] == "HIGH"


async def test_the_banks_original_statement_is_clean():
    doc, findings, _ = await _run("acb-2026-03")
    assert doc["integrity"]["verdict"] == "CLEAN"
    integrity = [f for f in findings if f["category"] in ("ARITHMETIC", "STRUCTURE", "EXTRACTION")]
    assert integrity == []
