"""Task queue port interface for workflow task enqueuing (spec 004 plan).

Enqueues document_workflow and month_workflow tasks.
"""

from typing import Protocol


class TaskQueue(Protocol):
    """Port for enqueuing workflow tasks to Cloud Tasks or inline runner."""

    async def enqueue_document_task(
        self, org_id: str, doc_id: str, run_id: str, attempt: int = 1
    ) -> str:
        """Enqueue doc-{docId}-{attempt} task to run the document workflow."""
        ...

    async def enqueue_month_task(
        self,
        org_id: str,
        month: str,
        generation: int,
        delay_seconds: int = 20,
    ) -> str:
        """Enqueue month-{orgId}-{yyyy-mm}-{generation} task with debounce delay."""
        ...
