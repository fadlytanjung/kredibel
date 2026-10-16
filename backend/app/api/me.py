"""GET /api/me: the signed-in user, and their workspace summary once they have one.

Normative references: spec 001 AC-001-4, AC-001-6; spec 013 AC-013-1; openapi Me.
"""

from contextlib import suppress
from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import ServiceProvider
from app.core.auth import Principal, PrincipalDependency
from app.core.errors import NotFoundError
from app.domain.plans import subscription_status, trial_days_left


def create_me_router(provider: ServiceProvider, principal_dep: PrincipalDependency) -> APIRouter:
    router = APIRouter(prefix="/api/me", tags=["system"])

    @router.get("")
    async def get_me(principal: Principal = Depends(principal_dep)) -> dict[str, Any]:
        workspace: dict[str, Any] | None = None
        ws = None
        if principal.org_id is not None:
            # A claim can outlive its workspace (never created, or a demo reset).
            with suppress(NotFoundError):
                ws = await provider.workspace_service.get(principal.org_id)
        if ws is not None:
            now = provider.clock.now()
            workspace = {
                "name": ws.name,
                "entityType": ws.entity_type,
                "planId": ws.subscription.plan_id,
                "subscriptionStatus": subscription_status(ws.subscription, now),
                "trialDaysLeft": trial_days_left(ws.subscription, now),
            }
        # A claim for a workspace that does not exist is no workspace: onboarding, not a dashboard.
        org_id = principal.org_id if ws is not None else None
        return {
            "uid": principal.uid,
            "email": principal.email,
            "displayName": principal.display_name,
            "orgId": org_id,
            "role": principal.role if ws is not None else None,
            "needsWorkspace": org_id is None,
            # Spec 021: onboarding offers the demo company when the server has its template.
            "demoAvailable": provider.workspace_service.demo_available,
            "language": "en",
            "workspace": workspace,
        }

    return router
