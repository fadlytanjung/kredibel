"""Unit tests for structlog JSON logging and request middleware (T001-08)."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_t001_08_logging_middleware_adds_request_id():
    """Logging middleware executes and processes requests with request-id header."""
    from app.core.logging import LoggingMiddleware, setup_logging

    setup_logging(log_level="INFO", project_id="cloud-hack2skill")
    app = FastAPI()
    app.add_middleware(LoggingMiddleware, project_id="cloud-hack2skill")

    @app.get("/ping")
    async def ping():
        return {"ping": "pong"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ping", headers={"X-Request-ID": "test-req-123"})

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "test-req-123"
