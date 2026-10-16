"""The extraction store's workspace routes (spec 022): POST /api/extractions/rebuild (AC-022-3),
every read document's chunks and Markdown rebuilt from what is stored; GET /api/extractions/search
(AC-022-6), the chunks nearest to a question, within the workspace."""

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import ServiceProvider
from app.api.documents import chunk_body
from app.core.auth import Principal


def create_extractions_router(provider: ServiceProvider, workspace_dep: Any) -> APIRouter:
    router = APIRouter(prefix="/api/extractions", tags=["documents"])

    @router.post("/rebuild")
    async def rebuild(principal: Principal = Depends(workspace_dep)) -> dict[str, Any]:
        return await provider.extraction_service.rebuild_all(principal)

    @router.get("/search")
    async def search(
        q: str = Query(min_length=2, max_length=500),
        limit: int = Query(default=8, ge=1, le=20),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        found = await provider.extraction_service.search(principal, q, limit)
        return {
            "items": [
                {
                    **chunk_body(chunk),
                    "fileName": name,
                    "similarity": round(similarity, 4),
                    "pageUrl": f"/api/documents/{chunk.doc_id}/pages/{chunk.page_no}/extraction.md",
                }
                for chunk, similarity, name in found
            ]
        }

    return router
