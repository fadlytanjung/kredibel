"""Firebase Hosting serves the SPA with the same headers as kredibel-web (ADR-018, docs/14 §8)."""

import json
from pathlib import Path

from app.core.security_headers import SECURITY_HEADERS

_FIREBASE_JSON = Path(__file__).resolve().parents[3] / "firebase.json"


def _hosting_headers(source: str) -> dict[str, str]:
    hosting = json.loads(_FIREBASE_JSON.read_text())["hosting"]
    for block in hosting.get("headers", []):
        if block["source"] == source:
            return {h["key"]: h["value"] for h in block["headers"]}
    return {}


def test_adr018_hosting_sends_the_security_headers_on_every_path():
    assert _hosting_headers("**") == SECURITY_HEADERS


def test_adr018_hosting_caches_hashed_assets_and_never_index_html():
    assert "immutable" in _hosting_headers("/assets/**")["Cache-Control"]
    assert _hosting_headers("/index.html")["Cache-Control"] == "no-cache"
