"""SPA static serving and fallback (T001-12, docs/16 §5)."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.static import mount_static_spa
from app.core.errors import register_error_handlers


@pytest.fixture
def spa_client(tmp_path: Path):
    static_dir = tmp_path / "static"
    (static_dir / "assets").mkdir(parents=True)
    (static_dir / "index.html").write_text("<html>spa</html>")
    (static_dir / "assets" / "index-abc123.js").write_text("console.log(1)")
    (tmp_path / "secret.txt").write_text("outside the static root")

    app = FastAPI()
    register_error_handlers(app)
    mount_static_spa(app, static_dir=str(static_dir))
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.parametrize(
    "path",
    [
        "/..%2Fsecret.txt",
        "/%2e%2e/secret.txt",
        "/assets/..%2F..%2Fsecret.txt",
    ],
)
async def test_t001_12_encoded_dot_segments_never_escape_the_static_root(spa_client, path):
    async with spa_client as client:
        res = await client.get(path)

    assert "outside the static root" not in res.text


async def test_t001_12_unknown_client_route_falls_back_to_index(spa_client):
    async with spa_client as client:
        res = await client.get("/months/2026-03")

    assert res.status_code == 200
    assert res.text == "<html>spa</html>"


async def test_t001_12_hashed_assets_are_served_with_long_cache(spa_client):
    async with spa_client as client:
        res = await client.get("/assets/index-abc123.js")

    assert res.status_code == 200
    assert "immutable" in res.headers["cache-control"]


async def test_t001_12_api_and_tasks_paths_never_fall_back_to_the_spa(spa_client):
    async with spa_client as client:
        api_res = await client.get("/api/unknown")
        tasks_res = await client.get("/tasks/unknown")

    assert api_res.status_code == 404
    assert api_res.headers["content-type"] == "application/problem+json"
    assert tasks_res.status_code == 404
