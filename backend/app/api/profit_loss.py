"""Management P&L and explicit company classifications (spec 018)."""

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import ServiceProvider, org_of
from app.api.insights import PERIOD
from app.core.auth import Principal
from app.domain.profit_loss import Classification, ProfitLoss


def create_profit_loss_router(provider: ServiceProvider, workspace_dep: Any) -> APIRouter:
    router = APIRouter(prefix="/api/profit-loss", tags=["insight"])

    @router.get("", response_model=ProfitLoss)
    async def report(
        period: str = Query(default="recent", pattern=PERIOD),
        principal: Principal = Depends(workspace_dep),
    ) -> ProfitLoss:
        return await provider.profit_loss_service.report(org_of(principal), period)

    @router.get("/accounts")
    async def accounts(principal: Principal = Depends(workspace_dep)) -> dict[str, Any]:
        return await provider.profit_loss_service.accounts(org_of(principal))

    @router.put("/accounts", response_model=Classification)
    async def confirm(
        body: Classification, principal: Principal = Depends(workspace_dep)
    ) -> Classification:
        return await provider.profit_loss_service.confirm(
            org_of(principal), principal.uid, principal.role, body
        )

    return router
