"""Cloud Tasks execution router for background worker jobs.

Normative reference: docs/specs/001-foundation/spec.md AC-001-10.
"""

from typing import Any

from fastapi import APIRouter


def create_tasks_router() -> APIRouter:
    """Create tasks router mounted only on worker/all roles."""
    router = APIRouter(prefix="/tasks", tags=["tasks"])

    @router.get("/health")
    async def get_tasks_health() -> dict[str, str]:
        return {"status": "ok", "component": "tasks"}

    @router.post("/document/{doc_id}")
    async def process_document_task(doc_id: str) -> dict[str, Any]:
        return {"status": "queued", "docId": doc_id}

    @router.post("/month/{org_id}/{month}")
    async def process_month_task(org_id: str, month: str) -> dict[str, Any]:
        return {"status": "queued", "orgId": org_id, "month": month}

    return router
