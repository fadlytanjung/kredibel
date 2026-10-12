"""Reading end to end without a model: upload → parse → classify → read → ground → bank lines
(spec 005, ADR-023). The reader is recorded from the synthetic statement's truth, printed as the
statement prints it; everything else is the real code path."""

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
from app.domain.models.document import DocStatus
from app.domain.models.workspace import Subscription
from app.domain.reading import (
    StatementHeader,
    StatementPageReading,
    StatementRowReading,
    StatementTotals,
)
from app.main import AppDeps, create_app
from tests.fakes.bank_line_repository import FakeBankLineRepository
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
TRUTH = json.loads((FIXTURES / "acb-2026-03.truth.json").read_text())


def _printed(value: str | None) -> str | None:
    return None if value is None else f"{Decimal(value):,.2f}"


def _recorded_page(page: int) -> StatementPageReading:
    rows = [r for r in TRUTH["rows"] if r["page"] == page]
    readings = [
        StatementRowReading(
            row_on_page=i + 1,
            date_text=f"{date.fromisoformat(r['date']):%d/%m/%Y}",
            description=r["description"],
            debit_text=_printed(r["debit"]),
            credit_text=_printed(r["credit"]),
            balance_text=_printed(r["balance"]),
        )
        for i, r in enumerate(rows)
    ]
    if page == 1:
        opening = StatementRowReading(
            row_on_page=0,
            date_text="01/03/2026",
            description="OPENING BALANCE",
            balance_text=_printed(TRUTH["opening"]),
        )
        readings = [opening, *readings]
        header = StatementHeader(
            bank_name="Archipelago Commerce Bank",
            account_holder=TRUTH["holder"],
            account_number=TRUTH["accountNumber"],
            currency="IDR",
            period_start_text="01 Mar 2026",
            period_end_text="31 Mar 2026",
        )
        return StatementPageReading(page=1, header=header, rows=readings)
    totals = StatementTotals(closing_balance_text=_printed(TRUTH["closing"]))
    return StatementPageReading(page=page, rows=readings, totals=totals)


def _deps(lines: FakeBankLineRepository, docs: FakeDocumentRepository) -> AppDeps:
    workspaces = FakeWorkspaceRepository()
    usage = FakeUsageRepository(workspaces=workspaces)
    usage.subscriptions["org_1"] = Subscription(
        plan_id="free_trial", status="TRIALING", trial_ends_at=datetime(2026, 10, 25, tzinfo=UTC)
    )
    settings = Settings(app_role="all", task_queue_mode="inline", month_run_delay_seconds=0)  # type: ignore[arg-type]
    return AppDeps(
        settings,
        load_plans(PLANS_FILE),
        workspace_repo=workspaces,
        usage_repo=usage,
        identity=FakeIdentityAdmin(),
        run_repo=FakeRunRepository(),
        month_repo=FakeMonthRepository(),
        doc_repo=docs,
        storage=FakeDocumentStorage(),
        renderer=DefaultPageRenderer(),
        spreadsheet_reader=DefaultSpreadsheetReader(),
        clock=FixedClock(datetime(2026, 4, 2, tzinfo=UTC)),
        reader=FakeDocumentReader(pages=_recorded_page),
        bank_lines=lines,
        token_verifier=FakeTokenVerifier(
            {"owner": {"uid": "u-1", "orgId": "org_1", "role": "owner"}}
        ),
    )


async def test_a_statement_upload_ends_with_grounded_bank_lines():
    lines, docs = FakeBankLineRepository(), FakeDocumentRepository()
    deps = _deps(lines, docs)
    app = create_app(deps.settings, deps=deps)
    pdf = (FIXTURES / "acb-2026-03.pdf").read_bytes()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        res = await c.post(
            "/api/documents",
            files={"file": ("acb.pdf", io.BytesIO(pdf), "application/pdf")},
            headers={"Authorization": "Bearer owner"},
        )
    assert res.status_code == 201, res.text
    queue = deps.task_queue
    assert isinstance(queue, InlineTaskQueue)
    await queue.drain()

    doc = await docs.get_document("org_1", res.json()["docId"])
    assert doc is not None
    assert doc.status == DocStatus.DONE, doc.status_detail
    assert doc.doc_type.value == "BANK_STATEMENT"
    assert doc.months == ["2026-03"]
    assert doc.reading is not None and doc.reading["agreement"] == 1.0
    assert doc.statement_meta is not None
    assert doc.statement_meta["accountMasked"] == "••••" + TRUTH["accountNumber"][-4:]
    assert doc.statement_meta["openingMinor"] == int(Decimal(TRUTH["opening"]) * 100)
    assert doc.statement_meta["closingMinor"] == int(Decimal(TRUTH["closing"]) * 100)

    stored = await lines.list_lines("org_1", doc_id=doc.doc_id)
    assert len(stored) == len(TRUTH["rows"])
    for line, row in zip(stored, TRUTH["rows"], strict=True):
        expected = Decimal(row["credit"]) if row["credit"] else -Decimal(row["debit"])
        assert (line.date.isoformat(), line.amount, line.balance) == (
            row["date"],
            expected,
            Decimal(row["balance"]),
        )
        assert line.consensus["amount"]["status"] == "AGREED"
        assert line.consensus["amount"]["bbox"] is not None


async def test_reading_twice_uses_the_page_cache():
    lines, docs = FakeBankLineRepository(), FakeDocumentRepository()
    deps = _deps(lines, docs)
    reader = deps.reader
    assert isinstance(reader, FakeDocumentReader)
    run = deps.document_workflow_runner
    app = create_app(deps.settings, deps=deps)
    pdf = (FIXTURES / "acb-2026-03.pdf").read_bytes()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        res = await c.post(
            "/api/documents",
            files={"file": ("acb.pdf", io.BytesIO(pdf), "application/pdf")},
            headers={"Authorization": "Bearer owner"},
        )
    queue = deps.task_queue
    assert isinstance(queue, InlineTaskQueue)
    await queue.drain()
    reads = [c for c in reader.calls if c[0] == "statement_page"]

    await run("org_1", res.json()["docId"], "run_again", 1)

    assert [c for c in reader.calls if c[0] == "statement_page"] == reads  # no new page reads


async def test_the_document_page_lists_the_lines_with_their_readings():
    lines, docs = FakeBankLineRepository(), FakeDocumentRepository()
    deps = _deps(lines, docs)
    app = create_app(deps.settings, deps=deps)
    pdf = (FIXTURES / "acb-2026-03.pdf").read_bytes()
    auth = {"Authorization": "Bearer owner"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        res = await c.post(
            "/api/documents",
            files={"file": ("acb.pdf", io.BytesIO(pdf), "application/pdf")},
            headers=auth,
        )
        queue = deps.task_queue
        assert isinstance(queue, InlineTaskQueue)
        await queue.drain()
        listed = await c.get("/api/bank-lines", params={"docId": res.json()["docId"]}, headers=auth)
        other = await c.get("/api/bank-lines", params={"docId": "doc_someone_else"}, headers=auth)

    assert listed.status_code == 200
    body = listed.json()
    assert len(body["items"]) == len(TRUTH["rows"])
    first = body["items"][0]
    assert (
        first["amount"]["amount"]
        == f"{Decimal(TRUTH['rows'][0]['credit'] or '-' + TRUTH['rows'][0]['debit']):.2f}"
    )
    assert first["readings"]["amount"]["status"] == "AGREED"
    assert first["readings"]["amount"]["bbox"] is not None
    assert first["readings"]["amount"]["sources"] == ["GEMINI", "TEXT_LAYER"]
    assert other.json()["items"] == []


async def test_the_document_carries_its_statement_in_contract_shape():
    lines, docs = FakeBankLineRepository(), FakeDocumentRepository()
    deps = _deps(lines, docs)
    app = create_app(deps.settings, deps=deps)
    pdf = (FIXTURES / "acb-2026-03.pdf").read_bytes()
    auth = {"Authorization": "Bearer owner"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        res = await c.post(
            "/api/documents",
            files={"file": ("acb.pdf", io.BytesIO(pdf), "application/pdf")},
            headers=auth,
        )
        queue = deps.task_queue
        assert isinstance(queue, InlineTaskQueue)
        await queue.drain()
        body = (await c.get(f"/api/documents/{res.json()['docId']}", headers=auth)).json()

    meta = body["statementMeta"]
    assert meta["opening"] == {"amount": f"{Decimal(TRUTH['opening']):.2f}", "currency": "IDR"}
    assert meta["closing"] == {"amount": f"{Decimal(TRUTH['closing']):.2f}", "currency": "IDR"}
    assert "openingMinor" not in meta
    assert body["reading"]["agreement"] == "1.000"
    assert body["reading"]["lines"] == len(TRUTH["rows"])
