"""Langfuse as the local trace viewer (ADR-026, T017-01b, AC-017-10). No network: exporters are
captured, spans stay in memory."""

import base64

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import SecretStr, ValidationError

from app.core.settings import Settings
from app.observability import tracing


@pytest.fixture(autouse=True)
def _fresh(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(tracing, "_configured", False)
    for key in ("TRACE_EXPORT", "LANGFUSE_HOST", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"):
        monkeypatch.delenv(key, raising=False)


def langfuse(**extra) -> Settings:
    return Settings(
        trace_export="langfuse",
        langfuse_public_key="pk-lf-test",
        langfuse_secret_key=SecretStr("sk-lf-test"),
        **extra,
    )  # type: ignore[arg-type]


def test_langfuse_export_needs_the_project_keys():
    with pytest.raises(ValidationError):
        Settings(trace_export="langfuse")  # type: ignore[arg-type]


def test_spans_go_to_the_langfuse_otel_endpoint_with_basic_auth(monkeypatch):
    exported: list[dict] = []
    providers: list[TracerProvider] = []
    monkeypatch.setattr(trace, "set_tracer_provider", providers.append)
    monkeypatch.setattr(
        tracing,
        "OTLPSpanExporter",
        lambda **kw: exported.append(kw) or InMemorySpanExporter(),
        raising=False,
    )
    tracing.setup_tracing(langfuse(langfuse_host="http://127.0.0.1:3000/"))

    (kw,) = exported
    assert kw["endpoint"] == "http://127.0.0.1:3000/api/public/otel/v1/traces"
    token = base64.b64encode(b"pk-lf-test:sk-lf-test").decode()
    assert kw["headers"] == {
        "Authorization": f"Basic {token}",
        "x-langfuse-ingestion-version": "4",
    }
    providers[0].shutdown()


def test_every_span_of_a_run_carries_its_session_user_and_tags():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(tracing.RunAttributes())
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")
    root = {
        "langfuse.trace.name": "document_workflow",
        "langfuse.session.id": "doc_1",
        "langfuse.user.id": "org_1",
        "langfuse.trace.tags": ("document_workflow",),
    }
    with (
        tracer.start_as_current_span("workflow:document_workflow", attributes=root),
        tracer.start_as_current_span("node:read_page"),
        tracer.start_as_current_span("generate_content gemini-3.8-flash"),
    ):
        pass
    for span in exporter.get_finished_spans():
        assert span.attributes is not None
        assert span.attributes["langfuse.trace.name"] == "document_workflow", span.name
        assert span.attributes["langfuse.session.id"] == "doc_1", span.name
        assert span.attributes["langfuse.user.id"] == "org_1", span.name
        assert span.attributes["langfuse.trace.tags"] == ("document_workflow",)
    provider.shutdown()
