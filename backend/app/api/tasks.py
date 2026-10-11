"""Worker router, mounted only on the worker and all roles (AC-001-10).

The task endpoints of docs/10 §2.9 (POST /tasks/process-document, POST /tasks/reconcile-month)
arrive with spec 004; until then only the health probe proves the router is mounted.
"""

from fastapi import APIRouter


def create_tasks_router() -> APIRouter:
    """Create tasks router mounted only on worker/all roles."""
    router = APIRouter(prefix="/tasks", tags=["tasks"])

    @router.get("/health")
    async def get_tasks_health() -> dict[str, str]:
        return {"status": "ok", "component": "tasks"}

    return router
