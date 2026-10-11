"""Integration tests for create_app mounting by role (T001-10, AC-001-1, AC-001-6, AC-001-10)."""

import pytest
from httpx import ASGITransport, AsyncClient

from tests.unit.test_auth import FakeTokenVerifier


@pytest.fixture
def fake_verifier():
    return FakeTokenVerifier(
        {
            "valid-owner": {
                "uid": "owner-1",
                "email": "owner@demo.kredibel",
                "name": "Jane Owner",
                "orgId": "org_demo",
                "role": "owner",
            }
        }
    )


@pytest.mark.asyncio
async def test_ac001_1_health_check_returns_ok_and_role():
    """GET /api/health returns status ok, version, and role."""
    from app.core.settings import Settings
    from app.main import create_app

    settings = Settings(app_role="all", app_version="0.1.0")
    app = create_app(settings=settings)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/health")

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert data["role"] == "all"


@pytest.mark.asyncio
async def test_ac001_10_web_role_mounts_api_me_but_not_tasks():
    """kredibel-web mounts /api/me but does not mount /tasks/*."""
    from app.core.settings import Settings
    from app.main import create_app

    settings = Settings(app_role="web")
    app = create_app(settings=settings)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # /api/me is mounted (returns 401 without token)
        me_res = await client.get("/api/me")
        assert me_res.status_code == 401

        # /tasks/* is absent (returns 404)
        task_res = await client.get("/tasks/document")
        assert task_res.status_code == 404


@pytest.mark.asyncio
async def test_ac001_10_worker_role_mounts_tasks_but_not_api_me():
    """kredibel-worker mounts /tasks/* but does not mount /api/* routes except /api/health."""
    from app.core.settings import Settings
    from app.main import create_app

    settings = Settings(app_role="worker")
    app = create_app(settings=settings)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # /api/health is present
        health_res = await client.get("/api/health")
        assert health_res.status_code == 200

        # /api/me is absent on worker (returns 404)
        me_res = await client.get("/api/me")
        assert me_res.status_code == 404

        # /tasks/* is present
        task_res = await client.get("/tasks/health")
        assert task_res.status_code == 200


@pytest.mark.asyncio
async def test_ac001_6_api_me_returns_principal_fields(fake_verifier):
    """GET /api/me returns uid, email, displayName, orgId, role, needsWorkspace, and language."""
    from app.adapters.policy_files import load_plans
    from app.core.settings import Settings
    from app.main import AppDeps, create_app
    from tests.fakes.usage_repository import FakeUsageRepository
    from tests.fakes.workspace_repository import FakeWorkspaceRepository, demo_workspace

    settings = Settings(app_role="web")
    workspaces = FakeWorkspaceRepository()
    workspaces.workspaces["org_demo"] = demo_workspace("org_demo")
    deps = AppDeps(
        settings,
        load_plans(settings.contract_path(settings.plans_file)),
        workspace_repo=workspaces,
        usage_repo=FakeUsageRepository(workspaces=workspaces),
        token_verifier=fake_verifier,
    )
    app = create_app(settings=settings, deps=deps)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/me", headers={"Authorization": "Bearer valid-owner"})

    assert res.status_code == 200
    data = res.json()
    assert data["workspace"]["name"] == "Synthetic Demo Ltd"
    assert data["uid"] == "owner-1"
    assert data["email"] == "owner@demo.kredibel"
    assert data["displayName"] == "Jane Owner"
    assert data["orgId"] == "org_demo"
    assert data["role"] == "owner"
    assert data["needsWorkspace"] is False
    assert data["language"] == "en"


@pytest.mark.asyncio
async def test_ac001_10_all_role_reaches_tasks_even_with_the_spa_fallback(tmp_path):
    """The SPA catch-all is registered last, so it never shadows /tasks or /api routes."""
    from app.core.settings import Settings
    from app.main import create_app

    (tmp_path / "index.html").write_text("<html>spa</html>")
    app = create_app(Settings(app_role="all", static_dir=str(tmp_path)))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tasks_res = await client.get("/tasks/health")
        spa_res = await client.get("/months/2026-03")

    assert tasks_res.status_code == 200
    assert spa_res.text == "<html>spa</html>"
