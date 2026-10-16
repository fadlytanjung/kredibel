"""POST /api/extractions/rebuild (spec 022, AC-022-3): every read document's chunks and Markdown
rebuilt from what is stored, with no model call. Owner or accountant."""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import ServiceProvider
from app.core.auth import Principal


def create_extractions_router(provider: ServiceProvider, workspace_dep: Any) -> APIRouter:
    router = APIRouter(prefix="/api/extractions", tags=["documents"])

    @router.post("/rebuild")
    async def rebuild(principal: Principal = Depends(workspace_dep)) -> dict[str, Any]:
        return await provider.extraction_service.rebuild_all(principal)

    return router
