"""Every plan limit reaches the client as its documented problem (T013-10, AC-013-7, AC-013-8).

The pure checks are unit-tested in test_entitlements.py; these tests go through the HTTP API with
the real plan catalog, so the status, code and limit fields are the ones the SPA reads.
"""

import io
from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image, ImageDraw

from app.adapters.page_renderer import DefaultPageRenderer
from app.adapters.policy_files import load_plans
from app.adapters.spreadsheet_reader import DefaultSpreadsheetReader
from app.core.settings import Settings
from app.domain.models.month import Month, MonthState
from app.domain.models.workspace import Subscription, UsageMonth
from app.main import AppDeps, create_app
from tests.fakes.clock import FixedClock
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.document_storage import FakeDocumentStorage
from tests.fakes.identity_admin import FakeIdentityAdmin
from tests.fakes.month_repository import FakeMonthRepository
from tests.fakes.run_repository import FakeRunRepository
from tests.fakes.task_queue import FakeTaskQueue
from tests.fakes.usage_repository import FakeUsageRepository
from tests.fakes.workspace_repository import FakeWorkspaceRepository
from tests.unit.test_auth import FakeTokenVerifier

PLANS_FILE = Path(__file__).resolve().parents[3] / "contracts" / "plans.v1.yaml"
NOW = datetime(2026, 10, 11, 8, 0, tzinfo=UTC)
TRIAL_ENDS = datetime(2026, 10, 25, tzinfo=UTC)
AUTH = {"Authorization": "Bearer owner"}


def _page_png() -> bytes:
    """A page with ink on it, so triage counts it as a page to read."""
    image = Image.new("RGB", (600, 800), "white")
    draw = ImageDraw.Draw(image)
    for row in range(12):
        draw.text((40, 40 + row * 50), f"05/03/2026  TRANSFER {row:02d}  1,250.00", fill="black")
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def _pdf(pages: int) -> bytes:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument.new()
    for _ in range(pages):
        pdf.new_page(width=200, height=200)
    out = io.BytesIO()
    pdf.save(out)
    pdf.close()
    return out.getvalue()


class Env:
    def __init__(self, trial_ends: datetime = TRIAL_ENDS) -> None:
        self.workspaces = FakeWorkspaceRepository()
        self.usage = FakeUsageRepository(workspaces=self.workspaces)
        self.usage.subscriptions["org_1"] = Subscription(
            plan_id="free_trial", status="TRIALING", trial_ends_at=trial_ends
        )
        self.task_queue = FakeTaskQueue()
        self.months = FakeMonthRepository()
        self.months.months[("org_1", "2026-03")] = Month(
            month="2026-03", state=MonthState.COLLECTING
        )
        tokens = FakeTokenVerifier(
            {"owner": {"uid": "u-1", "email": "o@example.test", "orgId": "org_1", "role": "owner"}}
        )
        settings = Settings(app_role="web")  # type: ignore[arg-type]
        deps = AppDeps(
            settings,
            load_plans(PLANS_FILE),
            workspace_repo=self.workspaces,
            usage_repo=self.usage,
            identity=FakeIdentityAdmin(),
            run_repo=FakeRunRepository(),
            month_repo=self.months,
            doc_repo=FakeDocumentRepository(),
            storage=FakeDocumentStorage(),
            task_queue=self.task_queue,
            renderer=DefaultPageRenderer(),
            spreadsheet_reader=DefaultSpreadsheetReader(),
            clock=FixedClock(NOW),
            token_verifier=tokens,
        )
        self.app = create_app(settings, deps=deps)

    def used(self, *, documents_uploaded: int = 0, pages_reserved: int = 0) -> None:
        self.usage.months[("org_1", "2026-10")] = UsageMonth(
            month="2026-10", documents_uploaded=documents_uploaded, pages_reserved=pages_reserved
        )

    def client(self) -> AsyncClient:
        return AsyncClient(transport=ASGITransport(app=self.app), base_url="http://test")


async def _upload(env: Env, name: str, body: bytes, media_type: str):
    async with env.client() as c:
        return await c.post(
            "/api/documents", files={"file": (name, body, media_type)}, headers=AUTH
        )


@pytest.fixture
def env() -> Env:
    return Env()


async def test_ac013_7_documents_per_month(env: Env):
    env.used(documents_uploaded=150)

    res = await _upload(env, "march.png", _page_png(), "image/png")

    assert res.status_code == 403
    body = res.json()
    assert body["code"] == "PLAN_LIMIT_REACHED"
    assert (body["limit"], body["used"], body["max"]) == ("documentsPerMonth", 150, 150)
    assert env.task_queue.enqueued_document_tasks == []


async def test_ac013_7_pages_read_per_month(env: Env):
    env.used(documents_uploaded=3, pages_reserved=400)

    res = await _upload(env, "march.png", _page_png(), "image/png")

    assert res.status_code == 403
    body = res.json()
    assert body["code"] == "PLAN_LIMIT_REACHED"
    assert (body["limit"], body["max"]) == ("extractedPagesPerMonth", 400)


async def test_ac013_7_file_size_is_413(env: Env):
    too_big = _pdf(1) + b"\0" * (21 * 1024 * 1024)

    res = await _upload(env, "big.pdf", too_big, "application/pdf")

    assert res.status_code == 413
    body = res.json()
    assert body["code"] == "DOCUMENT_TOO_LARGE"
    assert (body["limit"], body["max"]) == ("fileSizeMb", 20)


async def test_ac013_7_pages_per_document_is_422(env: Env):
    res = await _upload(env, "long.pdf", _pdf(21), "application/pdf")

    assert res.status_code == 422
    body = res.json()
    assert body["code"] == "TOO_MANY_PAGES"
    assert body["maxPages"] == 20


async def test_ac013_7_ledger_rows_per_file_is_422(env: Env):
    rows = "\n".join(f"2026-03-{1 + i % 28:02d},Sale {i},100.00" for i in range(5001))
    csv = f"date,description,amount\n{rows}\n".encode()

    res = await _upload(env, "ledger.csv", csv, "text/csv")

    assert res.status_code == 422
    body = res.json()
    assert body["code"] == "TOO_MANY_ROWS"
    assert (body["limit"], body["max"]) == ("ledgerRowsPerFile", 5000)


async def test_ac013_8_after_the_trial_uploads_and_reruns_stop_but_reading_works():
    env = Env(trial_ends=datetime(2026, 10, 1, tzinfo=UTC))

    upload = await _upload(env, "march.png", _page_png(), "image/png")
    async with env.client() as c:
        rerun = await c.post("/api/months/2026-03/reconcile", headers=AUTH)
        documents = await c.get("/api/documents", headers=AUTH)

    assert (upload.status_code, upload.json()["code"]) == (403, "TRIAL_EXPIRED")
    assert (rerun.status_code, rerun.json()["code"]) == (403, "TRIAL_EXPIRED")
    assert documents.status_code == 200
