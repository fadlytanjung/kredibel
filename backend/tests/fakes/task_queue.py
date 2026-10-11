"""In-memory fake task queue for tests."""

from app.ports.task_queue import TaskQueue


class FakeTaskQueue(TaskQueue):
    def __init__(self) -> None:
        self.enqueued_tasks: list[tuple[str, str, str]] = []

    async def enqueue_document_task(self, org_id: str, doc_id: str, run_id: str) -> str:
        self.enqueued_tasks.append((org_id, doc_id, run_id))
        return f"doc-{doc_id}-1"
