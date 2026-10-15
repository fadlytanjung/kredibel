"""Run tracking and stages routes (spec 004, AC-004-9), and the run's events with the labels it
produced (spec 017, AC-017-5…7).

Normative references:
- contracts/openapi.yaml /api/runs and /api/runs/{runId} endpoints
- AC-004-9: GET /api/runs/{runId} returns the run with its stages;
  GET /api/runs?target= lists a document's or a month's runs.
- docs/17-observability.md §5
"""

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import ServiceProvider, org_of
from app.core.auth import Principal
from app.domain.errors import ForbiddenError, NotFoundError
from app.domain.labels import Label
from app.domain.models.run import Run, RunKind, RunStage, RunStatus


def _stage_body(stage: RunStage) -> dict[str, Any]:
    return {
        "node": stage.node,
        "status": stage.status.value if hasattr(stage.status, "value") else str(stage.status),
        "startedAt": stage.started_at.isoformat() if stage.started_at else None,
        "endedAt": stage.ended_at.isoformat() if stage.ended_at else None,
        "model": stage.model,
        "tokensIn": stage.tokens_in,
        "tokensOut": stage.tokens_out,
        "traceSpanId": stage.trace_span_id,
        "parent": stage.parent,
        "summary": stage.summary,
    }


# The node each kind of label comes from (spec 016 writers), for the join on a run's events.
_LABEL_NODE = {
    "DOC_TYPE": "classify_document",
    "PAGE_TYPE": "verify_pages",
    "FIELD_VALUE": "verify_pages",
    "CATEGORY": "categorize_bank_lines",
    "COUNTERPARTY_ROLE": "build_counterparties",
}


def _label_counts(labels: list[Label]) -> dict[str, int]:
    return {
        "proposed": sum(1 for lb in labels if lb.status == "AI_PROPOSED"),
        "verified": sum(1 for lb in labels if lb.status == "VERIFIED"),
        "corrected": sum(1 for lb in labels if lb.status == "CORRECTED"),
    }


def _events(run: Run, labels: list[Label]) -> list[dict[str, Any]]:
    """The run's stages as events in time order: one NODE_OUTPUT per stage, an LLM_RESPONSE where a
    model was called, each with its latency, tokens, span and the labels that node produced."""
    by_node: dict[str, list[str]] = {}
    for lb in labels:
        by_node.setdefault(_LABEL_NODE.get(lb.task, ""), []).append(lb.label_id)
    ordered = sorted(
        enumerate(run.stages),
        key=lambda pair: (pair[1].started_at or run.created_at or 0, pair[0]),  # type: ignore[arg-type]
    )
    out: list[dict[str, Any]] = []
    for index, stage in ordered:
        started = stage.started_at or run.created_at
        latency = (
            int((stage.ended_at - stage.started_at).total_seconds() * 1000)
            if stage.started_at and stage.ended_at
            else None
        )
        status = stage.status.value if hasattr(stage.status, "value") else str(stage.status)
        base = {
            "node": stage.node,
            "agent": run.kind.value if hasattr(run.kind, "value") else str(run.kind),
            "at": started.isoformat() if started else None,
            "latencyMs": latency,
            "status": status,
            "spanId": stage.trace_span_id,
            "parentSpanId": stage.parent,
            "content": None,
        }
        out.append(
            {
                "eventId": f"{run.run_id}:{index}:{stage.node}",
                "eventType": "NODE_OUTPUT",
                **base,
                "model": None,
                "tokensIn": None,
                "tokensOut": None,
                "error": stage.summary if status == "FAILED" else None,
                "summary": stage.summary,
                "labelIds": by_node.get(stage.node, []),
            }
        )
        if stage.model:
            out.append(
                {
                    "eventId": f"{run.run_id}:{index}:{stage.node}:llm",
                    "eventType": "LLM_RESPONSE",
                    **base,
                    "parentSpanId": stage.trace_span_id,
                    "model": stage.model,
                    "tokensIn": stage.tokens_in,
                    "tokensOut": stage.tokens_out,
                    "error": None,
                    "summary": stage.summary,
                    "labelIds": by_node.get(stage.node, []),
                }
            )
    return out


def _run_body(run: Run, labels: list[Label] | None = None) -> dict[str, Any]:
    trace_url = (
        f"https://console.cloud.google.com/traces/list?tid={run.trace_id}" if run.trace_id else None
    )
    return {
        "runId": run.run_id,
        "kind": run.kind.value if hasattr(run.kind, "value") else str(run.kind),
        "target": run.target,
        "status": run.status.value if hasattr(run.status, "value") else str(run.status),
        "stages": [_stage_body(s) for s in run.stages],
        "traceId": run.trace_id,
        "traceUrl": trace_url,
        "models": run.models,
        "promptVersions": run.prompt_versions,
        "labels": _label_counts(labels)
        if labels is not None
        else (run.labels or {"proposed": 0, "verified": 0, "corrected": 0}),
        "usage": run.usage,
        "createdAt": run.created_at.isoformat() if run.created_at else None,
        "endedAt": run.ended_at.isoformat() if run.ended_at else None,
    }


def create_runs_router(
    provider: ServiceProvider,
    workspace_dep: Any,
) -> APIRouter:
    router = APIRouter(prefix="/api/runs", tags=["insight"])

    @router.get("")
    async def list_runs(
        kind: RunKind | None = Query(None),
        target: str | None = Query(None),
        run_status: RunStatus | None = Query(None, alias="status"),
        limit: int = Query(50, ge=1, le=200),
        cursor: str | None = Query(None),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        org_id = org_of(principal)
        runs = await provider.run_service.list_runs(
            org_id,
            kind=kind,
            target=target,
            status=run_status,
            limit=limit,
        )
        items = [_run_body(r, await provider.label_service.for_run(org_id, r.run_id)) for r in runs]
        return {"items": items, "nextCursor": None}

    @router.get("/{run_id}")
    async def get_run(
        run_id: str,
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        org_id = org_of(principal)
        run = await provider.run_service.get_run(org_id, run_id)
        if run is None:
            raise NotFoundError(f"Run '{run_id}' not found")
        return _run_body(run, await provider.label_service.for_run(org_id, run_id))

    @router.get("/{run_id}/events")
    async def list_run_events(
        run_id: str,
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        """AC-017-6: the run's events from its stages, joined to the labels it produced. Prompt and
        response content is not stored by this deployment, so `content` is always null."""
        if principal.role != "owner":
            raise ForbiddenError("Only the owner sees agent events.")
        org_id = org_of(principal)
        run = await provider.run_service.get_run(org_id, run_id)
        if run is None:
            raise NotFoundError(f"Run '{run_id}' not found")
        labels = await provider.label_service.for_run(org_id, run_id)
        return {"items": _events(run, labels), "contentCaptured": False}

    return router
