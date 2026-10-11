"""Workflow stage wrapper (AC-004-1, AC-004-12, docs/06 §2.2, docs/17)."""

import inspect
import json
from datetime import UTC, datetime
from typing import Any, cast

import structlog
from google.adk import Context
from google.adk.workflow import node
from google.adk.workflow._function_node import FunctionNode
from opentelemetry import trace
from structlog.contextvars import bind_contextvars, unbind_contextvars

from app.agents.deps import PipelineDeps
from app.domain.models.run import RunStage, StageStatus

_log = structlog.get_logger()
_tracer = trace.get_tracer("kredibel")


class CallableFunctionNode(FunctionNode):
    """ADK FunctionNode callable in unit tests."""

    async def __call__(self, ctx: Any = None, node_input: dict[str, Any] | None = None) -> Any:
        if node_input is None and isinstance(ctx, dict):
            node_input = ctx
            ctx = None
        sig = inspect.signature(self._func)
        if len(sig.parameters) >= 2 or (len(sig.parameters) == 1 and "ctx" in sig.parameters):
            return await self._func(ctx, node_input or {})
        return await self._func(node_input or {})


def node_input_dict(ctx: Any, node_input: Any) -> dict[str, Any]:
    """A node's input as a dict, from wherever this run supplied it (docs/23 §4)."""
    # Production passes the run input in session state (`node_input`); a previous node passes a
    # dict; in the ADK dev UI the developer types the input as a JSON chat message, or types
    # anything and the session state carries it.
    if isinstance(node_input, dict):
        return cast(dict[str, Any], node_input)
    if isinstance(node_input, str):
        try:
            parsed = json.loads(node_input)
        except ValueError:
            parsed = None
        if isinstance(parsed, dict):
            return cast(dict[str, Any], parsed)
    state = getattr(ctx, "state", None)
    state_data: dict[str, Any] = (
        cast(Any, state).to_dict() if state is not None and hasattr(state, "to_dict") else {}
    )
    from_state = state_data.get("node_input")
    return cast(dict[str, Any], from_state) if isinstance(from_state, dict) else state_data


def stage(
    deps: PipelineDeps,
    node_name: str,
    fn: Any | None = None,
) -> Any:
    """Wrap a node to record stages, bind logs, and trace spans."""

    def decorator(target_callable: Any) -> Any:
        raw_func = getattr(target_callable, "_func", target_callable)
        sig = inspect.signature(raw_func)
        accepts_ctx = len(sig.parameters) >= 2 or (
            len(sig.parameters) == 1 and "ctx" in sig.parameters
        )

        # `Any`, not dict: ADK coerces a node's input to its annotation, and the dev UI's first
        # node receives the chat message as text.
        async def _wrapped(ctx: Context, node_input: Any = None) -> dict[str, Any]:
            actual_input = node_input_dict(ctx, node_input)
            org_id = str(actual_input.get("orgId") or actual_input.get("org_id") or "")
            run_id = str(actual_input.get("runId") or actual_input.get("run_id") or "")
            doc_id = actual_input.get("docId") or actual_input.get("doc_id")
            month = actual_input.get("month")
            parent = actual_input.get("parent")
            if parent is not None:
                parent = str(parent)

            bind_kwargs: dict[str, Any] = {"node": node_name}
            if org_id:
                bind_kwargs["orgId"] = org_id
            if run_id:
                bind_kwargs["runId"] = run_id
            if doc_id:
                bind_kwargs["docId"] = doc_id
            if month:
                bind_kwargs["month"] = month
            bind_contextvars(**bind_kwargs)

            started_at = deps.clock.now() if deps.clock is not None else datetime.now(UTC)

            with _tracer.start_as_current_span(f"node:{node_name}") as span:
                if org_id:
                    span.set_attribute("orgId", org_id)
                if run_id:
                    span.set_attribute("runId", run_id)
                span.set_attribute("node", node_name)
                # Lets the ADK dev UI's Traces tab group our node spans with ADK's own spans.
                invocation_id = getattr(ctx, "invocation_id", None)
                if isinstance(invocation_id, str):
                    span.set_attribute("gcp.vertex.agent.invocation_id", invocation_id)
                if doc_id:
                    span.set_attribute("docId", str(doc_id))
                if month:
                    span.set_attribute("month", str(month))

                span_ctx = span.get_span_context()
                has_valid_span = span_ctx.is_valid and bool(span_ctx.span_id)
                span_id = f"{span_ctx.span_id:016x}" if has_valid_span else None

                try:
                    res_or_coro = (
                        raw_func(ctx, actual_input) if accepts_ctx else raw_func(actual_input)
                    )
                    if inspect.iscoroutine(res_or_coro):
                        result = await res_or_coro
                    else:
                        result = res_or_coro

                    ended_at = deps.clock.now() if deps.clock is not None else datetime.now(UTC)

                    duration_ms = int((ended_at - started_at).total_seconds() * 1000)

                    model = result.get("model") if isinstance(result, dict) else None
                    tokens_in = result.get("tokens_in") if isinstance(result, dict) else None
                    tokens_out = result.get("tokens_out") if isinstance(result, dict) else None
                    summary = result.get("summary") if isinstance(result, dict) else None

                    stage_record = RunStage(
                        node=node_name,
                        parent=parent,
                        status=StageStatus.DONE,
                        started_at=started_at,
                        ended_at=ended_at,
                        model=model,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        summary=summary,
                        trace_span_id=span_id,
                    )

                    if org_id and run_id:
                        await deps.run_repo.append_stage(org_id, run_id, stage_record)

                    _log.info(
                        "node.finished",
                        outcome="ok",
                        node=node_name,
                        durationMs=duration_ms,
                    )
                    return result if isinstance(result, dict) else {"result": result}
                except Exception as exc:
                    ended_at = deps.clock.now() if deps.clock is not None else datetime.now(UTC)
                    duration_ms = int((ended_at - started_at).total_seconds() * 1000)

                    stage_record = RunStage(
                        node=node_name,
                        parent=parent,
                        status=StageStatus.FAILED,
                        started_at=started_at,
                        ended_at=ended_at,
                        summary=str(exc),
                        trace_span_id=span_id,
                    )
                    if org_id and run_id:
                        await deps.run_repo.append_stage(org_id, run_id, stage_record)

                    _log.exception(
                        "node.failed",
                        outcome="error",
                        node=node_name,
                        durationMs=duration_ms,
                        error=str(exc),
                    )
                    raise
                finally:
                    unbind_contextvars("node")

        base_node = cast(Any, node(name=node_name)(_wrapped))
        base_node.__class__ = CallableFunctionNode
        return base_node

    if fn is not None:
        return decorator(fn)
    return decorator
