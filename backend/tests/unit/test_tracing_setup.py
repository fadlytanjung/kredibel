"""Trace export and content capture at start-up (docs/17 §2, ADR-017, T017-02)."""

import os

import pytest

from app.core.settings import Settings
from app.observability import tracing


@pytest.fixture(autouse=True)
def _fresh(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(tracing, "_configured", False)
    monkeypatch.delenv("ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS", raising=False)
    for key in ("TRACE_EXPORT", "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "K_SERVICE"):
        monkeypatch.delenv(key, raising=False)


def test_adr017_prompts_stay_out_of_spans_unless_the_data_is_synthetic():
    tracing.setup_tracing(Settings(ai_content_capture="off"))
    assert os.environ["ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS"] == "false"


def test_adr017_synthetic_capture_puts_prompts_in_spans(monkeypatch):
    tracing.setup_tracing(Settings(ai_content_capture="synthetic", data_class="synthetic"))
    assert os.environ["ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS"] == "true"


def test_ac004_12_cloud_export_uses_adk_gcp_exporters(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        tracing, "get_gcp_exporters", lambda **kw: calls.append(f"hooks:{kw}") or "hooks"
    )
    monkeypatch.setattr(
        tracing,
        "maybe_set_otel_providers",
        lambda otel_hooks_to_setup, otel_resource: calls.append(f"set:{otel_hooks_to_setup}"),
    )

    tracing.setup_tracing(Settings(trace_export="cloud", app_role="worker"))
    tracing.setup_tracing(Settings(trace_export="cloud", app_role="worker"))  # once only

    assert calls == ["hooks:{'enable_cloud_tracing': True}", "set:['hooks']"]


def test_no_export_by_default(monkeypatch):
    monkeypatch.setattr(tracing, "maybe_set_otel_providers", lambda **kw: pytest.fail("exported"))
    tracing.setup_tracing(Settings())


def test_local_otlp_exports_only_traces_once_without_google_credentials(monkeypatch):
    from opentelemetry import trace

    providers = []
    endpoints = []
    monkeypatch.setattr(trace, "set_tracer_provider", providers.append)
    monkeypatch.setattr(tracing, "get_gcp_exporters", lambda **kw: pytest.fail("Google export"))
    monkeypatch.setattr(tracing, "maybe_set_otel_providers", lambda **kw: pytest.fail("ADK export"))
    # Ambient generic OTLP configuration must not create duplicate traces or metrics/logs.
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://unused:9999")
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    monkeypatch.setattr(
        tracing,
        "OTLPSpanExporter",
        lambda *, endpoint: endpoints.append(endpoint) or InMemorySpanExporter(),
        raising=False,
    )
    settings = Settings(trace_export="otlp", app_role="worker")
    tracing.setup_tracing(settings)
    tracing.setup_tracing(settings)
    assert endpoints == ["http://127.0.0.1:4318/v1/traces"]
    assert len(providers) == 1
    assert providers[0].resource.attributes["service.name"] == "kredibel-worker"
    providers[0].shutdown()
