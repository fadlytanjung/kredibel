"""Integration tests for Finding routes (spec 008, AC-008-9)."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.adapters.policy_files import load_plans
from app.core.settings import Settings
from app.domain.findings import Finding
from app.domain.models.month import Month, MonthState
from app.main import AppDeps, create_app
from tests.fakes.clock import FixedClock
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.finding_repository import FakeFindingRepository
from tests.fakes.month_repository import FakeMonthRepository
from tests.fakes.workspace_repository import FakeWorkspaceRepository, demo_workspace
from tests.unit.test_auth import FakeTokenVerifier

PLANS_FILE = Path(__file__).resolve().parents[3] / "contracts" / "plans.v1.yaml"
AUTH = {"Authorization": "Bearer owner"}
NOW = datetime(2026, 3, 15, 10, 0, tzinfo=UTC)


@pytest.fixture
def findings_app():
    plans = load_plans(PLANS_FILE)
    clock = FixedClock(NOW)
    settings = Settings()
    workspaces = FakeWorkspaceRepository()
    month_repo = FakeMonthRepository()
    doc_repo = FakeDocumentRepository()
    finding_repo = FakeFindingRepository()

    # Pre-populate workspace
    ws = demo_workspace("org_demo")
    workspaces.workspaces["org_demo"] = ws

    deps = AppDeps(
        settings=settings,
        plans=plans,
        clock=clock,
        token_verifier=FakeTokenVerifier(
            {"owner": {"orgId": "org_demo", "role": "owner", "uid": "user_demo"}}
        ),
        workspace_repo=workspaces,
        month_repo=month_repo,
        doc_repo=doc_repo,
        findings=finding_repo,
    )
    app = create_app(settings=settings, deps=deps)
    return app, finding_repo, month_repo


@pytest.mark.asyncio
async def test_ac008_9_findings_api_get_and_patch(findings_app):
    app, finding_repo, month_repo = findings_app

    finding_id = "fnd_0123456789abcdef"
    finding = Finding(
        finding_id=finding_id,
        code="A01_RUNNING_BALANCE_BREAK",
        category="ARITHMETIC",
        severity="CRITICAL",
        title="Balance break on 14 Mar",
        facts={"diff": "6000000"},
        evidence=[],
        scope="MONTH",
        month="2026-03",
        status="OPEN",
    )
    await finding_repo.save_finding("org_demo", finding)

    month = Month(month="2026-03", state=MonthState.COLLECTING, dirty=False)
    await month_repo.save("org_demo", month)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /api/findings/{id}
        res_get = await client.get(f"/api/findings/{finding_id}", headers=AUTH)
        assert res_get.status_code == 200
        body = res_get.json()
        assert body["findingId"] == finding_id
        assert body["status"] == "OPEN"
        assert body["severity"] == "CRITICAL"

        # 2. PATCH /api/findings/{id} without reason on CRITICAL -> 422
        res_fail = await client.patch(
            f"/api/findings/{finding_id}",
            json={"status": "DISMISSED"},
            headers=AUTH,
        )
        assert res_fail.status_code == 422

        # 3. PATCH /api/findings/{id} with valid reason -> 200
        reason_text = "Verified with Archipelago Commerce Bank that this adjustment was legitimate."
        res_dismiss = await client.patch(
            f"/api/findings/{finding_id}",
            json={"status": "DISMISSED", "reason": reason_text},
            headers=AUTH,
        )
        assert res_dismiss.status_code == 200
        body_dismiss = res_dismiss.json()
        assert body_dismiss["status"] == "DISMISSED"
        assert body_dismiss["dismissal"]["reason"] == reason_text
        assert body_dismiss["dismissal"]["by"] == "user_demo"

        # Month was marked dirty
        saved_month = await month_repo.get("org_demo", "2026-03")
        assert saved_month is not None
        assert saved_month.dirty is True

        # 4. GET 404 on missing finding
        res_404 = await client.get("/api/findings/fnd_0000000000000000", headers=AUTH)
        assert res_404.status_code == 404
