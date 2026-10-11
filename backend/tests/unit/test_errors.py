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


def _app_with_routes() -> FastAPI:
    from app.core.errors import register_error_handlers

    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    async def boom():
        raise RuntimeError("secret internal detail")

    @app.get("/items/{item_id}")
    async def item(item_id: int):
        return {"id": item_id}

    return app


async def _get(app: FastAPI, path: str, method: str = "GET"):
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path)


async def test_t001_07_unknown_route_is_problem_json_not_found():
    res = await _get(_app_with_routes(), "/nowhere")

    assert res.status_code == 404
    assert res.headers["content-type"] == "application/problem+json"
    assert res.json()["code"] == "NOT_FOUND"


async def test_t001_07_wrong_method_is_problem_json():
    res = await _get(_app_with_routes(), "/boom", method="DELETE")

    assert res.status_code == 405
    assert res.headers["content-type"] == "application/problem+json"
    assert res.json()["code"] == "METHOD_NOT_ALLOWED"


async def test_t001_07_validation_error_lists_fields_without_echoing_input():
    res = await _get(_app_with_routes(), "/items/not-a-number")

    assert res.status_code == 422
    body = res.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["errors"][0]["field"] == "path.item_id"
    assert set(body["errors"][0]) == {"field", "message"}
    assert "not-a-number" not in res.text


async def test_t001_07_unexpected_error_is_internal_with_a_generic_detail():
    res = await _get(_app_with_routes(), "/boom")

    assert res.status_code == 500
    assert res.json()["code"] == "INTERNAL"
    assert "secret internal detail" not in res.text
