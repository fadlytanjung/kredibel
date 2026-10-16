"""Label writers for the workflow nodes (spec 016, AC-016-1): every automatic decision becomes a
label with its model, prompt version, run and span, merged over what a person already decided."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from opentelemetry import trace

from app.agents.deps import PipelineDeps
from app.domain.labels import AiDecision, Label, Source


def trace_ids() -> tuple[str | None, str | None]:
    """The current trace and span (the node's span), when tracing is on."""
    ctx = trace.get_current_span().get_span_context()
    if not ctx.is_valid:
        return None, None
    return f"{ctx.trace_id:032x}", f"{ctx.span_id:016x}"


def decision(
    value: str,
    *,
    source: Source,
    at: datetime,
    confidence: Decimal | float | None = None,
    model: str | None = None,
    prompt_version: str | None = None,
    run_id: Any = None,
    rule_id: str | None = None,
) -> AiDecision:
    trace_id, span_id = trace_ids()
    return AiDecision(
        value=value,
        source=source,
        at=at,
        confidence=Decimal(str(round(float(confidence), 4))) if confidence is not None else None,
        model=model,
        prompt_version=prompt_version,
        run_id=str(run_id) if run_id else None,
        trace_id=trace_id,
        span_id=span_id,
        rule_id=rule_id,
    )


async def write_labels(deps: PipelineDeps, org_id: str, labels: list[Label]) -> list[Label]:
    """Upsert through the repository (people win); a workspace without the store writes none."""
    if deps.labels is None or not labels:
        return []
    return await deps.labels.upsert(org_id, labels)


def page_image(doc_id: str, page_no: int | None) -> str:
    return f"/api/documents/{doc_id}/pages/{page_no or 1}"


def extraction_path(doc_id: str, page_no: int | None) -> str:
    """The API path of a page's extraction Markdown (AC-016-4)."""
    return f"/api/documents/{doc_id}/pages/{page_no or 1}/extraction.md"
