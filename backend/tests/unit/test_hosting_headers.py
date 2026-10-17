"""Firebase Hosting serves the SPA with the same headers as kredibel-web (ADR-018, docs/14 §8)."""

import json
from pathlib import Path

from app.core.security_headers import SECURITY_HEADERS

_FIREBASE_JSON = Path(__file__).resolve().parents[3] / "firebase.json"


def _blocks() -> list[dict]:
    return json.loads(_FIREBASE_JSON.read_text())["hosting"].get("headers", [])


def _hosting_headers(source: str) -> dict[str, str]:
    """Every block with this source, merged in order (Hosting applies all matching blocks)."""
    merged: dict[str, str] = {}
    for block in _blocks():
        if block["source"] == source:
            merged |= {h["key"]: h["value"] for h in block["headers"]}
    return merged


def test_adr018_hosting_sends_the_security_headers_on_every_path():
    assert SECURITY_HEADERS.items() <= _hosting_headers("**").items()


def test_adr018_hosting_caches_hashed_assets_and_never_a_page():
    """Every response is fetched fresh (index.html, each public route's own head, spec 020) unless
    it is a hashed asset (a year, immutable) or an image or font (a day). Hosting matches header
    rules on the request path, so the rule is the catch-all, and the asset rules come after it."""
    assert _hosting_headers("**")["Cache-Control"] == "no-cache"
    assert "immutable" in _hosting_headers("/assets/**")["Cache-Control"]
    sources = [
        b["source"] for b in _blocks() if any(h["key"] == "Cache-Control" for h in b["headers"])
    ]
    assert sources.index("**") < sources.index("/assets/**")
    assert any(
        "max-age=86400" in _hosting_headers(s).get("Cache-Control", "")
        for s in sources
        if "png" in s
    )
