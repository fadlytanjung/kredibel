"""Unit tests for SecurityHeadersMiddleware (T001-11)."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.security_headers import SecurityHeadersMiddleware


@pytest.mark.asyncio
async def test_t001_11_security_headers_present():
    """Responses include essential security headers (CSP, X-Content-Type-Options, Frame-Options)."""
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/test")
    async def hello():
        return {"hello": "world"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/test")

    assert res.status_code == 200
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in res.headers
