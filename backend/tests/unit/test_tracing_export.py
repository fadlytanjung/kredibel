"""TRACE_EXPORT=cloud must start: its exporters are built at app start on Cloud Run (docs/17 §2).

A missing exporter package once stopped the worker from starting; nothing ran this path in tests.
"""

import google.auth
import pytest
from google.adk.telemetry.google_cloud import get_gcp_exporters
from google.auth.credentials import AnonymousCredentials


def test_the_cloud_trace_exporters_can_be_built(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        google.auth, "default", lambda *a, **k: (AnonymousCredentials(), "test-project")
    )
    hooks = get_gcp_exporters(enable_cloud_tracing=True)
    assert hooks.span_processors


def test_spans_name_the_project_cloud_trace_files_them_under(monkeypatch: pytest.MonkeyPatch):
    """telemetry.googleapis.com answers 400 "Resource is missing required attribute
    gcp.project_id" to a resource without it, so production exported no workflow span."""
    from app.core.settings import Settings
    from app.observability import tracing

    captured: dict = {}
    monkeypatch.setattr(tracing, "_configured", False)
    monkeypatch.setattr(tracing, "get_gcp_exporters", lambda **_: "hooks")
    monkeypatch.setattr(tracing, "maybe_set_otel_providers", lambda **kw: captured.update(kw))
    settings = Settings(
        trace_export="cloud", google_cloud_project="test-project", app_role="worker"
    )  # type: ignore[call-arg]
    tracing.setup_tracing(settings)

    attributes = captured["otel_resource"].attributes
    assert attributes["gcp.project_id"] == "test-project"
    assert attributes["service.name"] == settings.service_name
    assert attributes["service.version"] == settings.app_version
