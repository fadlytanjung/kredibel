"""Integration tests for RUNS_ENABLED, quotas, and paused state (spec 004, AC-004-10, AC-004-11).

Normative references:
- AC-004-10: RUNS_ENABLED=false stops new tasks from being created
  (503 RUNS_DISABLED on upload and re-run); tasks already queued finish.
- AC-004-11: Month re-runs requested by a user are limited by monthRunsPerDay
  and RUN_QUOTA_PER_ORG_PER_DAY (429 RUN_QUOTA_EXCEEDED);
  automatic runs count too but are never dropped: past the limit they are delayed to the next day
  and the month shows "Reconciliation paused until tomorrow (daily limit)".
"""

import io
from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.adapters.page_renderer import DefaultPageRenderer
from app.adapters.policy_files import load_plans
from app.core.settings import Settings
from app.domain.models.month import Month, MonthState
from app.domain.models.workspace import Subscription, UsageDay
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

NOW = datetime(2026, 3, 15, 10, 0, tzinfo=UTC)
PLANS_FILE = Path(__file__).resolve().parents[3] / "contracts" / "plans.v1.yaml"


def _minimal_pdf() -> bytes:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument.new()
    pdf.new_page(width=200, height=200)
    out = io.BytesIO()
    pdf.save(out)
    pdf.close()
    return out.getvalue()


@pytest.fixture
def quota_env():
    def _builder(runs_enabled: bool = True, run_quota: int = 60):
        settings = Settings(
            app_role="web",
            runs_enabled=runs_enabled,
            run_quota_per_org_per_day=run_quota,
        )
        run_repo = FakeRunRepository()
        month_repo = FakeMonthRepository()
        doc_repo = FakeDocumentRepository()
        storage = FakeDocumentStorage()
        task_queue = FakeTaskQueue()
        renderer = DefaultPageRenderer()
        workspaces = FakeWorkspaceRepository()
        usage = FakeUsageRepository(workspaces=workspaces)
        usage.subscriptions["org_1"] = Subscription(
            plan_id="free_trial",
            status="ACTIVE",
            trial_ends_at=datetime(2026, 10, 25, 0, 0, tzinfo=UTC),
        )
        clock = FixedClock(NOW)
        identity = FakeIdentityAdmin()
        tokens = FakeTokenVerifier(
            {
                "ws1_user": {
                    "uid": "u-1",
                    "email": "user1@example.test",
                    "orgId": "org_1",
                    "role": "owner",
                },
            }
        )

        deps = AppDeps(
            settings=settings,
            plans=load_plans(PLANS_FILE),
            workspace_repo=workspaces,
            usage_repo=usage,
            run_repo=run_repo,
            month_repo=month_repo,
            doc_repo=doc_repo,
            storage=storage,
            renderer=renderer,
            task_queue=task_queue,
            identity=identity,
            clock=clock,
            token_verifier=tokens,
        )

        app = create_app(settings=settings, deps=deps, token_verifier=tokens)
        return app, deps, month_repo, usage, task_queue

    return _builder


@pytest.mark.asyncio
async def test_ac004_10_upload_when_runs_disabled_returns_503(quota_env):
    """Uploading a document when RUNS_ENABLED=false returns 503 RUNS_DISABLED (AC-004-10)."""
    app, _, _, _, _ = quota_env(runs_enabled=False)

    pdf_bytes = _minimal_pdf()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/documents",
            headers={"Authorization": "Bearer ws1_user"},
            files={"file": ("stmt.pdf", pdf_bytes, "application/pdf")},
        )
        assert resp.status_code == 503
        data = resp.json()
        assert data["code"] == "RUNS_DISABLED"


@pytest.mark.asyncio
async def test_ac004_10_reconcile_when_runs_disabled_returns_503(quota_env):
    """Triggering reconcile when RUNS_ENABLED=false returns 503 RUNS_DISABLED (AC-004-10)."""
    app, _, month_repo, _, _ = quota_env(runs_enabled=False)

    # Seed month
    month_repo.months[("org_1", "2026-03")] = Month(
        month="2026-03",
        state=MonthState.COLLECTING,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/months/2026-03/reconcile",
            headers={"Authorization": "Bearer ws1_user"},
        )
        assert resp.status_code == 503
        data = resp.json()
        assert data["code"] == "RUNS_DISABLED"


@pytest.mark.asyncio
async def test_ac004_11_user_request_within_quota_returns_202(quota_env):
    """User-requested month reconciliation returns 202 Accepted with runId (AC-004-11)."""
    app, _, month_repo, _, _ = quota_env(runs_enabled=True)

    month_repo.months[("org_1", "2026-03")] = Month(
        month="2026-03",
        state=MonthState.COLLECTING,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/months/2026-03/reconcile",
            headers={"Authorization": "Bearer ws1_user"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "runId" in data
        assert "month-org_1-2026-03-" in data["runId"]


@pytest.mark.asyncio
async def test_ac004_11_user_request_exceeding_quota_returns_429(quota_env):
    """User-requested month reconciliation past quota returns 429 RUN_QUOTA_EXCEEDED (AC-004-11)."""
    app, _, month_repo, usage, _ = quota_env(runs_enabled=True)

    month_repo.months[("org_1", "2026-03")] = Month(
        month="2026-03",
        state=MonthState.COLLECTING,
    )
    # Saturate quota
    usage.days[("org_1", "2026-03-15")] = UsageDay(day="2026-03-15", month_runs=60)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/months/2026-03/reconcile",
            headers={"Authorization": "Bearer ws1_user"},
        )
        assert resp.status_code == 429
        data = resp.json()
        assert data["code"] == "RUN_QUOTA_EXCEEDED"


@pytest.mark.asyncio
async def test_ac004_11_automatic_run_past_quota_pauses_until_tomorrow(quota_env):
    """Automatic month run past quota is not rejected; delayed and marked paused (AC-004-11)."""
    _, deps, month_repo, usage, task_queue = quota_env(runs_enabled=True)

    month_repo.months[("org_1", "2026-03")] = Month(
        month="2026-03",
        state=MonthState.COLLECTING,
    )
    # Saturate quota
    usage.days[("org_1", "2026-03-15")] = UsageDay(day="2026-03-15", month_runs=60)

    # Automatic trigger via month_service.mark_dirty
    run_ids = await deps.month_service.mark_dirty("org_1", ["2026-03"], reason="document_read")
    assert len(run_ids) == 1

    month_doc = await month_repo.get("org_1", "2026-03")
    assert month_doc is not None
    assert month_doc.note == "Reconciliation paused until tomorrow (daily limit)"

    # Task was enqueued with delay until tomorrow
    assert len(task_queue.enqueued_month_tasks) == 1
    _, _, _, delay = task_queue.enqueued_month_tasks[0]
    assert delay > 20
