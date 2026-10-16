"""Workspace routes: create, read, update (AC-013-2, -3, -11, -14, -15)."""

from typing import Any

from fastapi import APIRouter, Depends, status

from app.api.deps import ServiceProvider, org_of
from app.core.auth import Principal, PrincipalDependency
from app.domain.models.workspace import Workspace, WorkspaceCreate, WorkspaceUpdate
from app.domain.plans import subscription_status, trial_days_left


async def workspace_body(provider: ServiceProvider, workspace: Workspace) -> dict[str, Any]:
    """contracts/openapi.yaml Workspace; never exposes schemaVersion or account numbers."""
    now = provider.clock.now()
    entitlements = provider.entitlement_service
    sub = workspace.subscription
    month, day = await entitlements.usage(workspace.org_id)
    seats = await provider.workspace_service.seats_used(workspace.org_id)
    return {
        "orgId": workspace.org_id,
        "name": workspace.name,
        "entityType": workspace.entity_type,
        "profile": workspace.profile.model_dump(by_alias=True, exclude_none=True, mode="json"),
        "country": workspace.country,
        "timezone": workspace.timezone,
        "currency": workspace.currency,
        "defaultLanguage": workspace.default_language,
        "subscription": {
            "planId": sub.plan_id,
            "status": subscription_status(sub, now),
            "trialEndsAt": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
            "trialDaysLeft": trial_days_left(sub, now),
            "limits": entitlements.limits_for(sub).model_dump(by_alias=True, mode="json"),
        },
        "usage": {
            "month": month.month,
            "documentsUploaded": month.documents_uploaded,
            # Pages reserved or read this month; what the extractedPagesPerMonth limit counts.
            "extractedPages": month.pages_reserved,
            "monthRunsToday": day.month_runs,
            "assistantQuestionsToday": day.assistant_questions,
            "aiSpendUsd": str(month.ai_spend_usd),
            "seatsUsed": seats,
        },
        "learning": {"shareVerifiedLabels": workspace.share_verified_labels},
    }


def create_workspace_router(
    provider: ServiceProvider,
    principal_dep: PrincipalDependency,
    workspace_dep: PrincipalDependency,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["workspace"])

    @router.post("/workspaces", status_code=status.HTTP_201_CREATED)
    async def create_workspace(
        body: WorkspaceCreate, principal: Principal = Depends(principal_dep)
    ) -> dict[str, Any]:
        workspace = await provider.workspace_service.create(principal, body)
        return await workspace_body(provider, workspace)

    @router.post("/workspaces/demo", status_code=status.HTTP_201_CREATED)
    async def create_demo_workspace(
        principal: Principal = Depends(principal_dep),
    ) -> dict[str, Any]:
        """Spec 021: a workspace holding a copy of the demo company, owned by the caller."""
        workspace = await provider.workspace_service.create_demo(principal)
        return await workspace_body(provider, workspace)

    @router.get("/workspace")
    async def get_workspace(principal: Principal = Depends(workspace_dep)) -> dict[str, Any]:
        workspace = await provider.workspace_service.get(org_of(principal))
        return await workspace_body(provider, workspace)

    @router.patch("/workspace")
    async def update_workspace(
        body: WorkspaceUpdate, principal: Principal = Depends(workspace_dep)
    ) -> dict[str, Any]:
        workspace = await provider.workspace_service.update(principal, org_of(principal), body)
        return await workspace_body(provider, workspace)

    return router
