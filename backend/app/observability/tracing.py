"""OpenTelemetry for ADK workflows: Cloud Trace export and content capture (docs/17 §2, ADR-017).

ADK emits its own spans (`invocation`, `invoke_workflow`, `invoke_node`, `call_llm`,
`execute_tool`); `app/agents/runtime.py` adds a `workflow:<name>` root per run and
`app/agents/stages.py` a `node:<name>` span per node. This module decides where they go: Cloud
Trace when `TRACE_EXPORT=cloud` (Cloud Run), nowhere otherwise (tests and local runs; the ADK
dev UI keeps its own in-memory trace view).
"""

import os

import structlog
from google.adk.telemetry.google_cloud import get_gcp_exporters, get_gcp_resource
from google.adk.telemetry.setup import maybe_set_otel_providers
from opentelemetry.sdk.resources import Resource

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
    if _configured or settings.trace_export != "cloud":
        return
    hooks = get_gcp_exporters(enable_cloud_tracing=True)
    # ADK's resource names the project (gcp.project_id) and the Cloud Run service; without it
    # telemetry.googleapis.com refuses every batch with 400 and no span reaches Cloud Trace.
    resource = get_gcp_resource(settings.google_cloud_project).merge(
        Resource.create(
            {"service.name": settings.service_name, "service.version": settings.app_version}
        )
    )
    maybe_set_otel_providers(otel_hooks_to_setup=[hooks], otel_resource=resource)
    _configured = True
    _log.info("tracing.configured", exporter="cloud_trace")
