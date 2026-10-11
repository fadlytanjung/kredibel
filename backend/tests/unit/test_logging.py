"""JSON logging in the docs/17 §3 schema and the request middleware (T001-08)."""

import json

import pytest
import structlog
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.logging import LoggingMiddleware, setup_logging


def _last_json_line(captured: str) -> dict[str, object]:
    lines = [line for line in captured.splitlines() if line.startswith("{")]
    assert lines, f"no JSON log line in: {captured!r}"
    return json.loads(lines[-1])


async def _call(path: str, headers: dict[str, str] | None = None):
    app = FastAPI()
    app.add_middleware(LoggingMiddleware, project_id="demo-project")

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"ping": "pong"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(path, headers=headers or {})


@pytest.fixture(autouse=True)
def _logging():
    setup_logging(log_level="INFO", service="kredibel-web", version="abc1234")
    yield
    structlog.contextvars.clear_contextvars()


async def test_t001_08_request_id_is_echoed():
    response = await _call("/ping", {"X-Request-ID": "test-req-123"})

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "test-req-123"


async def test_nfr_log_line_carries_severity_message_service_version_and_trace(capsys):
    await _call("/ping", {"X-Cloud-Trace-Context": "105445aa7843bc8bf206b12000100000/1;o=1"})

    line = _last_json_line(capsys.readouterr().out)
    assert line["severity"] == "INFO"
    assert line["message"] == "request_finished"
    assert line["service"] == "kredibel-web"
    assert line["version"] == "abc1234"
    assert (
        line["logging.googleapis.com/trace"]
        == "projects/demo-project/traces/105445aa7843bc8bf206b12000100000"
    )
    assert "event" not in line and "level" not in line


async def test_nfr_traceparent_header_also_binds_the_trace(capsys):
    traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    await _call("/ping", {"traceparent": traceparent})

    line = _last_json_line(capsys.readouterr().out)
    assert (
        line["logging.googleapis.com/trace"]
        == "projects/demo-project/traces/4bf92f3577b34da6a3ce929d0e0e4736"
    )
