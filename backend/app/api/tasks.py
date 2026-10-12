"""Worker router mounted on worker and all roles (docs/10 §2.9, AC-004-1, AC-004-3, AC-004-5).

Handles Cloud Tasks delivery for:
- POST /tasks/process-document (runs document_workflow, idempotent by runId)
- POST /tasks/reconcile-month (runs month_workflow, superseded if generation < month.generation)
"""

from collections.abc import Callable, Coroutine
from typing import Any, Literal

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import ServiceProvider

_log = structlog.get_logger()

TaskAuthDep = Callable[..., Coroutine[Any, Any, None]]


class ProcessDocumentTask(BaseModel):
    orgId: str
    docId: str
    runId: str
    attempt: int = Field(default=1)


class ReconcileMonthTask(BaseModel):
    orgId: str
    month: str
    generation: int
    runId: str


# Cloud Tasks retries a task with the same body; its retry header says which attempt this is.
# kredibel-documents allows 3 attempts (infra/bootstrap.sh).
MAX_DOCUMENT_ATTEMPTS = 3


class TaskResult(BaseModel):
    ok: bool
    skipped: Literal["finished", "superseded"] | None = None


def create_tasks_router(
    deps: ServiceProvider,
    task_auth_dep: TaskAuthDep | None = None,
) -> APIRouter:
    """Create tasks router mounted only on worker/all roles."""
    router = APIRouter(prefix="/tasks", tags=["tasks"])
    auth_dependencies = [Depends(task_auth_dep)] if task_auth_dep is not None else []

    @router.get("/health")
    async def get_tasks_health() -> dict[str, str]:
        return {"status": "ok", "component": "tasks"}

    @router.post(
        "/process-document",
        response_model=TaskResult,
        status_code=status.HTTP_200_OK,
        dependencies=auth_dependencies,
    )
    async def process_document(
        task: ProcessDocumentTask,
        retry_count: int = Header(default=0, alias="X-CloudTasks-TaskRetryCount"),
    ) -> TaskResult:
        attempt = max(task.attempt, retry_count + 1)
        _log.info(
            "task_process_document_received",
            org_id=task.orgId,
            doc_id=task.docId,
            run_id=task.runId,
            attempt=attempt,
        )
        try:
            result = await deps.run_service.process_document_task(
                org_id=task.orgId,
                doc_id=task.docId,
                run_id=task.runId,
                attempt=attempt,
            )
            return TaskResult(
                ok=result.get("ok", True),
                skipped=result.get("skipped"),
            )
        except Exception as exc:
            _log.exception(
                "task_process_document_failed",
                org_id=task.orgId,
                doc_id=task.docId,
                run_id=task.runId,
                attempt=attempt,
                error=str(exc),
            )
            if attempt >= MAX_DOCUMENT_ATTEMPTS:
                # The last try: whatever failed (even before the workflow started), the person
                # sees a failed document instead of one waiting forever.
                try:
                    await deps.document_service.mark_failed(
                        task.orgId, task.docId, "E02_EXTRACTION_FAILED"
                    )
                except Exception:
                    _log.exception("task_mark_failed_failed", doc_id=task.docId)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Document processing failed: {exc}",
            ) from exc

    @router.post(
        "/reconcile-month",
        response_model=TaskResult,
        status_code=status.HTTP_200_OK,
        dependencies=auth_dependencies,
    )
    async def reconcile_month(task: ReconcileMonthTask) -> TaskResult:
        _log.info(
            "task_reconcile_month_received",
            org_id=task.orgId,
            month=task.month,
            generation=task.generation,
            run_id=task.runId,
        )
        try:
            result = await deps.run_service.reconcile_month_task(
                org_id=task.orgId,
                month=task.month,
                generation=task.generation,
                run_id=task.runId,
            )
            return TaskResult(
                ok=result.get("ok", True),
                skipped=result.get("skipped"),
            )
        except Exception as exc:
            _log.exception(
                "task_reconcile_month_failed",
                org_id=task.orgId,
                month=task.month,
                generation=task.generation,
                run_id=task.runId,
                error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Month reconciliation failed: {exc}",
            ) from exc

    return router
