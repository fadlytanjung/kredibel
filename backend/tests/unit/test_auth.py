"""Unit tests for Firebase authentication and Principal verification.

Traceability: T001-09, AC-001-4, AC-001-5.
"""

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient


class FakeTokenVerifier:
    """In-memory fake verifier for testing auth without contacting Firebase."""

    def __init__(self, valid_tokens: dict[str, dict]):
        self.valid_tokens = valid_tokens

    def verify_token(self, token: str) -> dict:
        if token in self.valid_tokens:
            return self.valid_tokens[token]
        raise ValueError("Invalid or expired token")


@pytest.fixture
def fake_verifier():
    return FakeTokenVerifier(
        {
            "valid-owner-token": {
                "uid": "user-123",
                "email": "owner@demo.kredibel",
                "name": "Jane Owner",
                "orgId": "org_demo",
                "role": "owner",
            },
            "valid-no-org-token": {
                "uid": "user-456",
                "email": "newuser@demo.kredibel",
                "name": "Bob New",
            },
        }
    )


def create_test_auth_app(verifier):
    from app.core.auth import get_principal_dependency, require_workspace
    from app.core.errors import register_error_handlers

    app = FastAPI()
    register_error_handlers(app)
    principal_dep = get_principal_dependency(verifier)

    @app.get("/api/me")
    async def get_me(principal=Depends(principal_dep)):
        return {
            "uid": principal.uid,
            "email": principal.email,
            "orgId": principal.org_id,
            "role": principal.role,
            "needsWorkspace": principal.org_id is None,
        }

    @app.get("/api/workspace-data")
    async def get_workspace_data(principal=Depends(require_workspace(principal_dep))):
        return {"orgId": principal.org_id, "data": "secret"}

    return app


@pytest.mark.asyncio
async def test_ac001_5_missing_header_returns_401(fake_verifier):
    """Missing Authorization header returns 401 UNAUTHENTICATED."""
    app = create_test_auth_app(fake_verifier)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/me")

    assert res.status_code == 401
    assert res.headers["content-type"] == "application/problem+json"
    assert res.json()["code"] == "UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_ac001_5_invalid_token_returns_401(fake_verifier):
    """Invalid token returns 401 UNAUTHENTICATED."""
    app = create_test_auth_app(fake_verifier)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/me", headers={"Authorization": "Bearer bad-token"})

    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_ac001_4_valid_token_without_org_returns_needs_workspace(fake_verifier):
    """Valid token without orgId returns 200 with needsWorkspace: true on /api/me."""
    app = create_test_auth_app(fake_verifier)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/me", headers={"Authorization": "Bearer valid-no-org-token"})

    assert res.status_code == 200
    data = res.json()
    assert data["uid"] == "user-456"
    assert data["orgId"] is None
    assert data["needsWorkspace"] is True


@pytest.mark.asyncio
async def test_ac001_4_workspace_scoped_route_returns_403_when_no_org(fake_verifier):
    """Calling workspace-scoped route without orgId returns 403 WORKSPACE_REQUIRED."""
    app = create_test_auth_app(fake_verifier)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/workspace-data", headers={"Authorization": "Bearer valid-no-org-token"}
        )

    assert res.status_code == 403
    assert res.headers["content-type"] == "application/problem+json"
    assert res.json()["code"] == "WORKSPACE_REQUIRED"


@pytest.mark.asyncio
async def test_valid_token_with_org_returns_principal(fake_verifier):
    """Valid token with orgId returns principal and allows workspace route."""
    app = create_test_auth_app(fake_verifier)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/workspace-data", headers={"Authorization": "Bearer valid-owner-token"}
        )

    assert res.status_code == 200
    assert res.json()["orgId"] == "org_demo"


@pytest.mark.asyncio
async def test_ac001_5_invalid_token_detail_does_not_echo_the_verifier_error():
    class LeakyVerifier:
        def verify_token(self, token: str) -> dict:
            raise ValueError("Firebase ID token has incorrect 'aud' claim: other-project")

    app = create_test_auth_app(LeakyVerifier())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/me", headers={"Authorization": "Bearer whatever"})

    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"
    assert "aud" not in res.text and "other-project" not in res.text
