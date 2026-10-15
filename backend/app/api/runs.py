"""Run tracking and stages routes (spec 004, AC-004-9).

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
from app.domain.errors import NotFoundError
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


def _run_body(run: Run) -> dict[str, Any]:
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
        "labels": run.labels or {"proposed": 0, "verified": 0, "corrected": 0},
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
        return {
            "items": [_run_body(r) for r in runs],
            "nextCursor": None,
        }

    @router.get("/{run_id}")
    async def get_run(
        run_id: str,
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        org_id = org_of(principal)
        run = await provider.run_service.get_run(org_id, run_id)
        if run is None:
            raise NotFoundError(f"Run '{run_id}' not found")
        return _run_body(run)

    return router
