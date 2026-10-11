"""Unit tests for RFC 9457 problem details error handling (T001-07)."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


def test_t001_07_domain_error_attributes():
    """DomainError has code, status, title, and detail and converts to problem dict."""
    from app.core.errors import DomainError

    err = DomainError(
        code="RESOURCE_LOCKED",
        status=409,
        title="Resource is locked",
        detail="The item is currently being reconciled.",
    )
    assert err.code == "RESOURCE_LOCKED"
    assert err.status == 409
    problem = err.to_problem()
    assert problem["status"] == 409
    assert problem["title"] == "Resource is locked"
    assert problem["detail"] == "The item is currently being reconciled."
    assert problem["code"] == "RESOURCE_LOCKED"
    assert "type" in problem


@pytest.mark.asyncio
async def test_t001_07_exception_handler_returns_problem_json():
    """FastAPI app with error handlers returns application/problem+json for DomainError."""
    from app.core.errors import DomainError, register_error_handlers

    app = FastAPI()
    register_error_handlers(app)

    @app.get("/trigger-error")
    async def trigger():
        raise DomainError(
            code="WORKSPACE_REQUIRED",
            status=403,
            title="Workspace required",
            detail="User has no workspace claim.",
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/trigger-error")

    assert response.status_code == 403
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["code"] == "WORKSPACE_REQUIRED"
    assert body["title"] == "Workspace required"
    assert body["status"] == 403
