"""The public demo account (spec 024, AC-024-3): it resets its own workspace to a fresh copy of the
demo company; nobody else can. Synthetic data only."""

from httpx import ASGITransport, AsyncClient

from app.adapters.policy_files import load_plans
from app.core.settings import Settings
from app.main import AppDeps, create_app
from tests.fakes.clock import FixedClock
from tests.fakes.identity_admin import FakeIdentityAdmin
from tests.fakes.usage_repository import FakeUsageRepository
from tests.fakes.workspace_copier import FakeWorkspaceCopier
from tests.fakes.workspace_repository import FakeWorkspaceRepository
from tests.integration.test_demo_workspace_api import NOW, PLANS_FILE, TEMPLATE, template
from tests.unit.test_auth import FakeTokenVerifier

DEMO = {"uid": "u-demo", "email": "demo@kredibel.test"}


async def _harness():
    workspaces = FakeWorkspaceRepository()
    await workspaces.create_workspace(template(), max_workspaces=200)
    identity, copier = FakeIdentityAdmin(), FakeWorkspaceCopier(workspaces=workspaces)
    tokens = FakeTokenVerifier(
        {"demo": dict(DEMO), "other": {"uid": "u-2", "email": "judge@example.test"}}
    )
    settings = Settings(
        app_role="web", demo_template_org=TEMPLATE, demo_account_email="demo@kredibel.test"
    )
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
    return client, workspaces, identity, copier, tokens


async def test_ac024_3_the_demo_account_resets_its_workspace_to_a_fresh_copy():
    client, workspaces, identity, copier, tokens = await _harness()
    async with client:
        first = await client.post(
            "/api/workspaces/demo/reset", headers={"Authorization": "Bearer demo"}
        )
        old = first.json()["orgId"]
        tokens.valid_tokens["demo"] = {**DEMO, "orgId": old, "role": "owner"}
        second = await client.post(
            "/api/workspaces/demo/reset", headers={"Authorization": "Bearer demo"}
        )
        other = await client.post(
            "/api/workspaces/demo/reset", headers={"Authorization": "Bearer other"}
        )

    assert first.status_code == 200 and second.status_code == 200, second.text
    new = second.json()["orgId"]
    assert new != old and old in copier.discarded
    assert identity.claims["u-demo"] == {"orgId": new, "role": "owner"}
    assert new in workspaces.workspaces
    assert other.status_code == 403
