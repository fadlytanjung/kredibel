"""Direct SDK attempts must be visible, without exporting document content (AC-017-9)."""

import pytest
from google.genai import errors
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from app.adapters import gemini_reader
from tests.unit.test_gemini_reader_retries import _ok, _reader


@pytest.fixture
def spans(monkeypatch):
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(gemini_reader, "_tracer", provider.get_tracer("test"), raising=False)
    yield exporter
    provider.shutdown()


async def test_retried_sdk_calls_share_parent_and_only_export_metadata(spans):
    secret = "PRIVATE_DOCUMENT_SENTINEL"
    limited = errors.ClientError(
        429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": secret}}
    )
    reader, _, _ = _reader([limited, _ok()])
    with gemini_reader._tracer.start_as_current_span("node:classify_document") as parent:
        await reader.classify(b"private image", secret)
    finished = spans.get_finished_spans()
    calls = [s for s in finished if s.name.startswith("generate_content ")]
    assert len(calls) == 2
    assert all(s.parent.span_id == parent.get_span_context().span_id for s in calls)
    assert [s.attributes["kredibel.attempt"] for s in calls] == [1, 2]
    assert calls[0].status.status_code == StatusCode.ERROR
    assert calls[0].attributes["error.type"] == "429"
    assert calls[1].attributes["gen_ai.usage.input_tokens"] == 10
    assert calls[1].attributes["gen_ai.usage.output_tokens"] == 5
    assert calls[1].attributes["kredibel.prompt_version"].startswith("classify_document")
    assert secret not in "\n".join(s.to_json() for s in finished)


async def test_invalid_model_output_does_not_export_validation_message(spans):
    bad = _ok()
    bad.parsed = {"doc_type": "PRIVATE_DOCUMENT_SENTINEL"}
    reader, _, _ = _reader([bad, _ok()])
    await reader.classify(b"png", "text")
    calls = spans.get_finished_spans()
    assert len(calls) == 2
    assert calls[0].status.status_code == StatusCode.ERROR
    assert "PRIVATE_DOCUMENT_SENTINEL" not in "\n".join(s.to_json() for s in calls)
