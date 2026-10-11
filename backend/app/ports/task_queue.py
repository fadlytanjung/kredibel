"""Task queue port interface for workflow task enqueuing (spec 003 plan).

Enqueues document_workflow and month_workflow tasks.
"""

from typing import Protocol


class TaskQueue(Protocol):
    async def enqueue_document_task(self, org_id: str, doc_id: str, run_id: str) -> str:
        """Enqueue doc-{docId}-1 task to run the document workflow."""
        ...
