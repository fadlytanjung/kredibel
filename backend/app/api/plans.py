"""GET /api/plans: the catalog, coming-soon features and UI languages (AC-013-6)."""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import ServiceProvider
from app.core.auth import Principal, PrincipalDependency


def create_plans_router(provider: ServiceProvider, principal_dep: PrincipalDependency) -> APIRouter:
    router = APIRouter(prefix="/api/plans", tags=["workspace"])

    @router.get("")
    async def list_plans(_: Principal = Depends(principal_dep)) -> dict[str, Any]:
        catalog = provider.plans
        return {
            "plans": [
                plan.model_dump(
                    by_alias=True, exclude_none=True, exclude={"after_trial"}, mode="json"
                )
                for plan in catalog.plans
            ],
            "comingSoonFeatures": [
                f.model_dump(by_alias=True, exclude_none=True) for f in catalog.coming_soon_features
            ],
            "languages": [lang.model_dump(by_alias=True) for lang in catalog.languages],
        }

    return router
