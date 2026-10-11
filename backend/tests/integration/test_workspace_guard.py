"""Without a workspace only a few routes work; every other /api route is 403 (T013-04, AC-013-1).

The check walks the real app's route table, so a route added later without `require_workspace`
fails here instead of leaking another workspace's data to a user who has none.
"""

import re

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient

from app.core.settings import Settings
from app.main import create_app
from tests.unit.test_auth import FakeTokenVerifier

NO_WORKSPACE = FakeTokenVerifier({"no-org": {"uid": "u-new", "email": "new@example.test"}})

# AC-013-1 and docs/10 §1: what a signed-in user without a workspace may call.
OPEN_WITHOUT_WORKSPACE = {
    ("GET", "/api/health"),
    ("GET", "/api/me"),
    ("GET", "/api/plans"),
    ("POST", "/api/workspaces"),
    ("POST", "/api/invites/{inviteId}/accept"),
}


async def unguarded_api_routes(app: FastAPI) -> list[str]:
    leaks: list[str] = []
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for route in app.routes:
            if not isinstance(route, APIRoute) or not route.path.startswith("/api/"):
                continue
            for method in sorted((route.methods or set()) - {"HEAD", "OPTIONS"}):
                if (method, route.path) in OPEN_WITHOUT_WORKSPACE:
                    continue
                url = re.sub(r"\{[^}]+\}", "x", route.path)
                res = await client.request(
                    method, url, headers={"Authorization": "Bearer no-org"}, json={}
                )
                if res.status_code != 403 or res.json().get("code") != "WORKSPACE_REQUIRED":
                    leaks.append(f"{method} {route.path} -> {res.status_code}")
    return leaks


async def test_ac013_1_every_other_api_route_requires_a_workspace():
    app = create_app(Settings(app_role="web"), token_verifier=NO_WORKSPACE)

    assert await unguarded_api_routes(app) == []


async def test_ac013_1_the_guard_check_catches_an_unguarded_route():
    app = create_app(Settings(app_role="web"), token_verifier=NO_WORKSPACE)
    rogue = APIRouter()

    @rogue.get("/api/leak")
    async def leak() -> dict[str, str]:
        return {"other": "workspace data"}

    # Ahead of the SPA catch-all, where a real router would be mounted.
    app.router.routes[0:0] = rogue.routes

    assert await unguarded_api_routes(app) == ["GET /api/leak -> 200"]


async def test_ac013_1_me_without_a_workspace_says_so():
    app = create_app(Settings(app_role="web"), token_verifier=NO_WORKSPACE)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/me", headers={"Authorization": "Bearer no-org"})

    assert res.status_code == 200
    assert res.json()["orgId"] is None
    assert res.json()["needsWorkspace"] is True
