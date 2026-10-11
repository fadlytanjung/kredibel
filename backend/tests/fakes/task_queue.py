"""In-memory fake task queue for tests."""

from app.ports.task_queue import TaskQueue


class FakeTaskQueue(TaskQueue):
    def __init__(self) -> None:
        self.enqueued_document_tasks: list[tuple[str, str, str, int]] = []
        self.enqueued_month_tasks: list[tuple[str, str, int, int]] = []

    @property
    def enqueued_tasks(self) -> list[tuple[str, str, str]]:
        return [(org, doc, run) for org, doc, run, _ in self.enqueued_document_tasks]

    async def enqueue_document_task(
        self, org_id: str, doc_id: str, run_id: str, attempt: int = 1
    ) -> str:
        self.enqueued_document_tasks.append((org_id, doc_id, run_id, attempt))
        return f"doc-{doc_id}-{attempt}"

    async def enqueue_month_task(
        self,
        org_id: str,
        month: str,
        generation: int,
        delay_seconds: int = 20,
    ) -> str:
        self.enqueued_month_tasks.append((org_id, month, generation, delay_seconds))
        return f"month-{org_id}-{month}-{generation}"
