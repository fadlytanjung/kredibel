"""Run one ADK workflow as one traced run (AC-004-12, docs/17 §2, docs/23 §3)."""

# Every run gets a `workflow:<name>` root span, so its node spans and ADK's own `invoke_workflow`,
# `invoke_node`, `call_llm` and `execute_tool` spans form one trace; the trace ID is stored on the
# run (`runs.traceId`) and bound to every log line, so a run opens in Cloud Trace and Logs Explorer.

import json
from typing import Any, cast

import structlog
from google.adk import Runner, Workflow
from google.adk.sessions import InMemorySessionService
from opentelemetry import context as otel_context
from opentelemetry import trace
from structlog.contextvars import bind_contextvars, unbind_contextvars

from app.core.logging import TRACE_FIELD
from app.core.settings import Settings
from app.observability.agent_analytics import agent_analytics_plugins
from app.ports.run_repository import RunRepository

_tracer = trace.get_tracer("kredibel")
_log = structlog.get_logger()

APP_NAME = "kredibel"


def adk_user_id(org_id: str) -> str:
    """ADR-017: every ADK user_id starts with the workspace, so events filter by workspace."""
    return f"{org_id}:system"


async def run_workflow(
    workflow: Workflow,
    *,
    org_id: str,
    run_id: str,
    node_input: dict[str, Any],
    run_repo: RunRepository,
    settings: Settings,
) -> dict[str, Any]:
    """Execute `workflow` with the run input in session state; returns the last node's output."""
    attributes = {k: str(v) for k, v in node_input.items() if k in ("docId", "month", "generation")}
    # Langfuse (ADR-026) groups a document's or a month's runs as one session, a workspace's as
    # one user; tracing.RunAttributes copies these onto every span of the run.
    session = node_input.get("docId") or f"month:{node_input.get('month')}"
    viewer = {
        "langfuse.trace.name": workflow.name,
        "langfuse.session.id": str(session),
        "langfuse.user.id": org_id,
        "langfuse.trace.tags": (workflow.name,),
    }
    # One run, one trace: a run started inside another run (the inline queue runs a month task
    # within the document run that queued it) starts its own trace, linked to the run that caused
    # it.
    current = trace.get_current_span()
    caused_by = getattr(current, "name", "").startswith("workflow:")
    with _tracer.start_as_current_span(
        f"workflow:{workflow.name}",
        context=otel_context.Context() if caused_by else None,
        links=[trace.Link(current.get_span_context())] if caused_by else None,
        attributes={
            "orgId": org_id,
            "runId": run_id,
            "workflow": workflow.name,
            **attributes,
            **viewer,
        },
    ) as span:
        # The run's input and outcome as identifiers only, never document content (ADR-026): a
        # viewer's default "with input and output" view then lists every run.
        ids = {"workflow": workflow.name, "runId": run_id, **attributes}
        span.set_attribute("langfuse.observation.input", json.dumps(ids, sort_keys=True))
        context = span.get_span_context()
        trace_bound = context.is_valid
        if trace_bound:
            trace_id = format(context.trace_id, "032x")
            await run_repo.set_trace_id(org_id, run_id, trace_id)
            bind_contextvars(
                **{TRACE_FIELD: f"projects/{settings.google_cloud_project}/traces/{trace_id}"}
            )
        try:
            # Sessions live only for the run: domain state is in Firestore, not ADK (docs/06 §8).
            sessions = InMemorySessionService()
            runner = Runner(
                agent=cast(Any, workflow),
                app_name=APP_NAME,
                session_service=sessions,
                plugins=agent_analytics_plugins(settings),  # spec 017, off unless enabled
            )
            user_id = adk_user_id(org_id)
            await sessions.create_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=run_id,
                state={"node_input": node_input},
            )
            last: dict[str, Any] = {}
            async for event in runner.run_async(user_id=user_id, session_id=run_id):
                output = getattr(event, "output", None)
                if isinstance(output, dict):
                    last = cast(dict[str, Any], output)
            span.set_attribute("langfuse.observation.output", json.dumps({"outcome": "done"}))
            return last
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.Status(trace.StatusCode.ERROR, type(exc).__name__))
            failed = {"outcome": "failed", "error": type(exc).__name__}
            span.set_attribute("langfuse.observation.output", json.dumps(failed))
            raise
        finally:
            if trace_bound:
                unbind_contextvars(TRACE_FIELD)
