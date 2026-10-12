"""Month reconciliation and inquiry routes (spec 004, AC-004-10, AC-004-11).

Normative references:
- contracts/openapi.yaml /api/months endpoints
- AC-004-10: RUNS_ENABLED=false stops new tasks from being created
  (503 RUNS_DISABLED on upload and re-run)
- AC-004-11: Month re-runs requested by a user are limited by monthRunsPerDay
  and RUN_QUOTA_PER_ORG_PER_DAY (429 RUN_QUOTA_EXCEEDED)
"""

from typing import Any

from fastapi import APIRouter, Depends, status

from app.api.deps import ServiceProvider, org_of
from app.core.auth import Principal
from app.domain.errors import NotFoundError
from app.domain.models.month import Month


def _month_body(month: Month) -> dict[str, Any]:
    return {
        "month": month.month,
        "state": month.state.value if hasattr(month.state, "value") else str(month.state),
        "dirty": month.dirty,
        "generation": month.generation,
        "statements": month.statements,
        "figures": month.figures,
        "risk": month.risk,
        "flows": month.flows,
        "note": month.note,
        "lastRunId": month.last_run_id,
        "updatedAt": month.updated_at.isoformat() if month.updated_at else None,
    }


def create_months_router(
    provider: ServiceProvider,
    workspace_dep: Any,
) -> APIRouter:
    router = APIRouter(prefix="/api/months", tags=["months"])

    @router.get("")
    async def list_months(
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        org_id = org_of(principal)
        months = await provider.month_service.list_months(org_id)
        return {"items": [_month_body(m) for m in months]}

    @router.get("/{month}")
    async def get_month(
        month: str,
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        org_id = org_of(principal)
        month_doc = await provider.month_service.get_month(org_id, month)
        if month_doc is None:
            raise NotFoundError(f"Month '{month}' not found")
        return _month_body(month_doc)

    @router.post("/{month}/reconcile", status_code=status.HTTP_202_ACCEPTED)
    async def reconcile_month(
        month: str,
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        org_id = org_of(principal)
        month_doc = await provider.month_service.get_month(org_id, month)
        if month_doc is None:
            raise NotFoundError(f"Month '{month}' not found")

        run = await provider.run_service.start_month_run(org_id, month, is_user_request=True)
        return {"runId": run.run_id}

    return router
