"""Open a demo company (spec 021, AC-021-1…3): a new workspace for the caller with the template's
profile, its records copied with the IDs swapped, claims set, two events; no template is a 503, a
person with a workspace gets a 409, and a failed copy leaves nothing. Synthetic data only."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from app.adapters.policy_files import load_plans
from app.core.settings import Settings
from app.domain.models.workspace import Profile, Subscription, Workspace
from app.main import AppDeps, create_app
from app.ports.workspace_repository import NewWorkspace, OwnerMember
from tests.fakes.clock import FixedClock
from tests.fakes.identity_admin import FakeIdentityAdmin
from tests.fakes.usage_repository import FakeUsageRepository
from tests.fakes.workspace_copier import FakeWorkspaceCopier
from tests.fakes.workspace_repository import FakeWorkspaceRepository
from tests.unit.test_auth import FakeTokenVerifier

PLANS_FILE = Path(__file__).resolve().parents[3] / "contracts" / "plans.v1.yaml"
NOW = datetime(2026, 10, 16, 3, 0, tzinfo=UTC)
TEMPLATE = "org_demo_template"
AUTH = {"Authorization": "Bearer new"}


def template() -> NewWorkspace:
    return NewWorkspace(
        workspace=Workspace(
            org_id=TEMPLATE,
            name="Sunrise Coffee Roasters",
            entity_type="COMPANY",
            profile=Profile(legal_name="Sunrise Coffee Roasters", industry="Food and drink"),
            country="ID",
            timezone="Asia/Jakarta",
            currency="IDR",
            default_language="en",
            subscription=Subscription(
                plan_id="free_trial",
                status="TRIALING",
                trial_started_at=NOW,
                trial_ends_at=NOW + timedelta(days=400),
                limit_overrides={"documentsPerMonth": 600},
            ),
            created_by="u_template",
            created_at=NOW,
        ),
        owner=OwnerMember(uid="u_template", email="template@demo.kredibel", display_name=None),
    )


async def harness(*, template_org: str = TEMPLATE, fail: bool = False, seed: bool = True):
    workspaces = FakeWorkspaceRepository()
    if seed:
        await workspaces.create_workspace(template(), max_workspaces=15)
    identity = FakeIdentityAdmin()
    copier = FakeWorkspaceCopier(fail=fail)
    tokens = FakeTokenVerifier({"new": {"uid": "u-1", "email": "judge@example.test"}})
    settings = Settings(app_role="web", demo_template_org=template_org)
    deps = AppDeps(
        settings,
        load_plans(PLANS_FILE),
        workspace_repo=workspaces,
        usage_repo=FakeUsageRepository(workspaces=workspaces),
        identity=identity,
        clock=FixedClock(NOW),
        token_verifier=tokens,
        workspace_copier=copier,
    )
    client = AsyncClient(
        transport=ASGITransport(app=create_app(settings, deps=deps), raise_app_exceptions=False),
        base_url="http://test",
    )
    return client, workspaces, identity, copier


async def test_ac021_1_the_demo_company_is_copied_into_a_new_workspace_owned_by_the_caller():
    client, workspaces, identity, copier = await harness()
    async with client:
        me = (await client.get("/api/me", headers=AUTH)).json()
        res = await client.post("/api/workspaces/demo", headers=AUTH)
    assert me["demoAvailable"] is True and me["needsWorkspace"] is True
    assert res.status_code == 201, res.text
    body = res.json()
    org_id = body["orgId"]
    assert org_id != TEMPLATE and body["name"] == "Sunrise Coffee Roasters"
    assert body["currency"] == "IDR" and body["timezone"] == "Asia/Jakarta"
    assert body["subscription"]["limits"]["documentsPerMonth"] == 150, "the plan's, not the demo's"
    assert copier.copies == [(TEMPLATE, org_id, {TEMPLATE: org_id, "u_template": "u-1"})]
    assert copier.fields == [(TEMPLATE, org_id)] and copier.discarded == []
    assert identity.claims["u-1"] == {"orgId": org_id, "role": "owner"}
    assert [e.type for e in workspaces.events[org_id]] == ["WORKSPACE_CREATED", "DEMO_COPIED"]
    assert workspaces.workspaces[TEMPLATE].name == "Sunrise Coffee Roasters", "template unchanged"


async def test_ac021_3_no_template_means_no_demo():
    client, _, _, copier = await harness(template_org="")
    async with client:
        me = (await client.get("/api/me", headers=AUTH)).json()
        res = await client.post("/api/workspaces/demo", headers=AUTH)
    assert me["demoAvailable"] is False
    assert res.status_code == 503 and res.json()["code"] == "DEMO_UNAVAILABLE"
    assert copier.copies == []

    client, _, _, _ = await harness(seed=False)
    async with client:
        missing = await client.post("/api/workspaces/demo", headers=AUTH)
    assert missing.status_code == 503


async def test_ac021_3_a_person_with_a_workspace_gets_a_409():
    client, _, identity, copier = await harness()
    async with client:
        first = await client.post("/api/workspaces/demo", headers=AUTH)
        org_id = first.json()["orgId"]
        second = await client.post("/api/workspaces/demo", headers=AUTH)
    assert second.status_code == 409 and second.json()["code"] == "ALREADY_IN_WORKSPACE"
    assert identity.claims["u-1"]["orgId"] == org_id
    assert len(copier.discarded) == 1, "the second copy is removed"


async def test_ac021_2_a_failed_copy_leaves_nothing():
    client, workspaces, identity, copier = await harness(fail=True)
    async with client:
        res = await client.post("/api/workspaces/demo", headers=AUTH)
    assert res.status_code == 500
    target = copier.copies[0][1]
    assert copier.discarded == [target] and target not in workspaces.workspaces
    assert "u-1" not in identity.claims
