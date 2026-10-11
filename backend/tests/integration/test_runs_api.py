"""Integration tests for Runs API endpoints (spec 004, AC-004-9).

Normative references:
- AC-004-9: GET /api/runs/{runId} returns the run with its stages;
  GET /api/runs?target= lists a document's or a month's runs.
- contracts/openapi.yaml /api/runs and /api/runs/{runId}
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.adapters.policy_files import load_plans
from app.core.settings import Settings
from app.domain.models.run import Run, RunKind, RunStage, RunStatus, StageStatus
from app.domain.models.workspace import Subscription
from app.main import AppDeps, create_app
from tests.fakes.clock import FixedClock
from tests.fakes.identity_admin import FakeIdentityAdmin
from tests.fakes.month_repository import FakeMonthRepository
from tests.fakes.run_repository import FakeRunRepository
from tests.fakes.task_queue import FakeTaskQueue
from tests.fakes.usage_repository import FakeUsageRepository
from tests.fakes.workspace_repository import FakeWorkspaceRepository
from tests.unit.test_auth import FakeTokenVerifier

NOW = datetime(2026, 3, 15, 10, 0, tzinfo=UTC)
PLANS_FILE = Path(__file__).resolve().parents[3] / "contracts" / "plans.v1.yaml"


@pytest.fixture
def runs_app():
    settings = Settings(app_role="web", runs_enabled=True)
    run_repo = FakeRunRepository()
    month_repo = FakeMonthRepository()
    workspaces = FakeWorkspaceRepository()
    usage = FakeUsageRepository(workspaces=workspaces)
    usage.subscriptions["org_1"] = Subscription(
        plan_id="free_trial",
        status="ACTIVE",
        trial_ends_at=datetime(2026, 10, 25, 0, 0, tzinfo=UTC),
    )
    usage.subscriptions["org_2"] = Subscription(
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
            "ws2_user": {
                "uid": "u-2",
                "email": "user2@example.test",
                "orgId": "org_2",
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
        identity=identity,
        clock=clock,
        task_queue=FakeTaskQueue(),
        token_verifier=tokens,
    )

    app = create_app(settings=settings, deps=deps, token_verifier=tokens)
    return app, run_repo


@pytest.mark.asyncio
async def test_ac004_9_get_run_with_stages(runs_app):
    """GET /api/runs/{runId} returns the run with its stages (AC-004-9)."""
    app, run_repo = runs_app

    run_id = "doc-doc_abc-1"
    stage_1 = RunStage(
        node="read_pages",
        status=StageStatus.DONE,
        started_at=NOW,
        ended_at=NOW,
        model="gemini-2.5-flash",
        tokens_in=100,
        tokens_out=50,
        summary="read 2 pages",
    )
    run = Run(
        run_id=run_id,
        kind=RunKind.DOCUMENT,
        target="doc_abc",
        status=RunStatus.DONE,
        stages=[stage_1],
        trace_id="trace_123",
        created_at=NOW,
        ended_at=NOW,
    )
    await run_repo.create("org_1", run)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/runs/{run_id}",
            headers={"Authorization": "Bearer ws1_user"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["runId"] == run_id
        assert data["kind"] == "DOCUMENT"
        assert data["target"] == "doc_abc"
        assert data["status"] == "DONE"
        assert data["traceId"] == "trace_123"
        assert len(data["stages"]) == 1
        assert data["stages"][0]["node"] == "read_pages"
        assert data["stages"][0]["status"] == "DONE"
        assert data["stages"][0]["summary"] == "read 2 pages"


@pytest.mark.asyncio
async def test_ac004_9_get_run_not_found(runs_app):
    """GET /api/runs/{runId} returns 404 when run does not exist."""
    app, _ = runs_app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/runs/doc-nonexistent-1",
            headers={"Authorization": "Bearer ws1_user"},
        )
        assert resp.status_code == 404
        data = resp.json()
        assert data["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_ac004_9_list_runs_by_target(runs_app):
    """GET /api/runs?target= returns list of runs for a document or month."""
    app, run_repo = runs_app

    # Create 2 runs for doc_target and 1 run for doc_other
    run_1 = Run(
        run_id="doc-doc_target-1",
        kind=RunKind.DOCUMENT,
        target="doc_target",
        status=RunStatus.DONE,
        created_at=NOW,
    )
    run_2 = Run(
        run_id="doc-doc_target-2",
        kind=RunKind.DOCUMENT,
        target="doc_target",
        status=RunStatus.RUNNING,
        created_at=NOW,
    )
    run_other = Run(
        run_id="doc-doc_other-1",
        kind=RunKind.DOCUMENT,
        target="doc_other",
        status=RunStatus.DONE,
        created_at=NOW,
    )
    await run_repo.create("org_1", run_1)
    await run_repo.create("org_1", run_2)
    await run_repo.create("org_1", run_other)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/runs?target=doc_target",
            headers={"Authorization": "Bearer ws1_user"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) == 2
        run_ids = {r["runId"] for r in data["items"]}
        assert run_ids == {"doc-doc_target-1", "doc-doc_target-2"}


@pytest.mark.asyncio
async def test_ac004_9_tenant_isolation(runs_app):
    """A user in org_2 cannot access runs from org_1."""
    app, run_repo = runs_app

    run_org1 = Run(
        run_id="doc-doc_secret-1",
        kind=RunKind.DOCUMENT,
        target="doc_secret",
        status=RunStatus.DONE,
        created_at=NOW,
    )
    await run_repo.create("org_1", run_org1)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/runs/doc-doc_secret-1",
            headers={"Authorization": "Bearer ws2_user"},
        )
        assert resp.status_code == 404
