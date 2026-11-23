"""Security headers of docs/14 §8 on every response (T001-11).

The expected values are read from the table in docs/14 §8, so the doc stays the single source.
"""

import re
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.security_headers import SecurityHeadersMiddleware

_DOC = Path(__file__).resolve().parents[3] / "docs" / "14-security-and-compliance.md"
_ROW = re.compile(r"^\| `([A-Za-z-]+)` \| `([^`]+)`", re.MULTILINE)


def documented_headers() -> dict[str, str]:
    section = _DOC.read_text().split("## 8. Web security", 1)[1].split("\n## ", 1)[0]
    return dict(_ROW.findall(section))


def _client() -> AsyncClient:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/api/thing")
    async def thing() -> dict[str, str]:
        return {"ok": "yes"}

    @app.get("/docs")
    async def docs() -> dict[str, str]:
        return {"docs": "page"}

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def test_t001_11_doc_table_lists_the_five_headers():
    assert set(documented_headers()) == {
        "Content-Security-Policy",
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "Referrer-Policy",
        "Permissions-Policy",
    }


@pytest.mark.parametrize("path", ["/api/thing", "/index.html-route"])
async def test_t001_11_every_response_carries_the_documented_headers(path):
    async with _client() as client:
        res = await client.get(path)

    for name, value in documented_headers().items():
        assert res.headers.get(name) == value, name


async def test_t001_11_api_docs_page_only_adds_its_cdn():
    async with _client() as client:
        res = await client.get("/docs")

    csp = res.headers["Content-Security-Policy"]
    expected_script = "script-src 'self' 'unsafe-inline' https://apis.google.com https://cdn.jsdelivr.net"
    assert expected_script in csp
    assert "frame-ancestors 'none'" in csp


async def test_every_api_response_an_error_too_is_never_kept_by_a_cache():
    """docs/14 §8: Firebase Hosting's CDN kept a 404 of /api/workspace for every caller."""
    async with _client() as client:
        ok = await client.get("/api/thing")
        missing = await client.get("/api/no-such-thing")
        page = await client.get("/index.html-route")

    assert ok.headers.get("Cache-Control") == "no-store"
    assert missing.status_code == 404
    assert missing.headers.get("Cache-Control") == "no-store"
    assert page.headers.get("Cache-Control") is None  # the SPA's own caching is Hosting's
