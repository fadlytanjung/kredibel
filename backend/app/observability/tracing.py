"""OpenTelemetry for ADK workflows: Cloud Trace export and content capture (docs/17 §2, ADR-017).

ADK emits its own spans (`invocation`, `invoke_workflow`, `invoke_node`, `call_llm`,
`execute_tool`); `app/agents/runtime.py` adds a `workflow:<name>` root per run and
`app/agents/stages.py` a `node:<name>` span per node. This module decides where they go: Cloud
Trace when `TRACE_EXPORT=cloud`, local OTLP/HTTP when `otlp`, nowhere when `none`.
The ADK dev UI keeps its own in-memory trace view.
"""

import os

import structlog
from google.adk.telemetry.google_cloud import get_gcp_exporters, get_gcp_resource
from google.adk.telemetry.setup import maybe_set_otel_providers
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.settings import Settings

_log = structlog.get_logger()
_configured = False


def setup_tracing(settings: Settings) -> None:
    """Configure once per process, before the first workflow runs."""
    global _configured
    # ADK reads this per span. Prompts and responses are recorded only with synthetic data
    # (non-negotiable 17); Settings already refuses synthetic capture on real data.
    os.environ["ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS"] = (
        "true" if settings.capture_span_content else "false"
    )
    if _configured or settings.trace_export == "none":
        return
    service = Resource.create(
        {"service.name": settings.service_name, "service.version": settings.app_version}
    )
    if settings.trace_export == "otlp":
        # Explicitly traces only. ADK's helper also exports logs/metrics when a generic OTLP
        # endpoint is in the environment; Jaeger accepts traces, and needs no Google credentials.
        provider = TracerProvider(resource=service)
        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_traces_endpoint)
            )
        )
        trace.set_tracer_provider(provider)
        _configured = True
        _log.info("tracing.configured", exporter="otlp_http")
        return
    hooks = get_gcp_exporters(enable_cloud_tracing=True)
    # ADK's resource names the project (gcp.project_id) and the Cloud Run service; without it
    # telemetry.googleapis.com refuses every batch with 400 and no span reaches Cloud Trace.
    resource = get_gcp_resource(settings.google_cloud_project).merge(service)
    maybe_set_otel_providers(otel_hooks_to_setup=[hooks], otel_resource=resource)
    _configured = True
    _log.info("tracing.configured", exporter="cloud_trace")
