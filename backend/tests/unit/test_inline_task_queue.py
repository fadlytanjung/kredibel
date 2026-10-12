"""Local dev runs the worker in-process: the inline queue calls the task handlers (docs/13 §7,
docs/16 §1, AC-004-3), with the retries Cloud Tasks would give."""

import asyncio
import json

from app.adapters.cloud_tasks import CloudTasksQueue, InlineTaskQueue


async def test_a_document_task_runs_the_handler_in_process():
    calls: list[tuple[str, str, str, int]] = []

    async def on_document(org_id: str, doc_id: str, run_id: str, attempt: int) -> None:
        calls.append((org_id, doc_id, run_id, attempt))

    queue = InlineTaskQueue(on_document=on_document, retry_delay_seconds=0)
    name = await queue.enqueue_document_task("org_1", "doc_1", "run_1")
    await queue.drain()

    assert name == "doc-doc_1-1"
    assert calls == [("org_1", "doc_1", "run_1", 1)]


async def test_a_failing_document_task_is_retried_up_to_the_third_attempt():
    attempts: list[int] = []

    async def on_document(org_id: str, doc_id: str, run_id: str, attempt: int) -> None:
        attempts.append(attempt)
        raise RuntimeError("reader unavailable")

    queue = InlineTaskQueue(on_document=on_document, retry_delay_seconds=0)
    await queue.enqueue_document_task("org_1", "doc_1", "run_1")
    await queue.drain()

    assert attempts == [1, 2, 3]


async def test_a_month_task_waits_its_delay_and_carries_the_run_id():
    seen: list[tuple[str, str, int, str]] = []

    async def on_month(org_id: str, month: str, generation: int, run_id: str) -> None:
        seen.append((org_id, month, generation, run_id))

    queue = InlineTaskQueue(on_month=on_month, retry_delay_seconds=0)
    await queue.enqueue_month_task("org_1", "2026-03", 4, delay_seconds=0)
    await queue.drain()

    assert seen == [("org_1", "2026-03", 4, "month-org_1-2026-03-4")]


async def test_without_handlers_the_queue_only_records_tasks():
    queue = InlineTaskQueue()
    await queue.enqueue_document_task("org_1", "doc_1", "run_1")
    await queue.drain()
    assert queue.enqueued_document_tasks[0]["runId"] == "run_1"


def test_the_cloud_month_task_body_names_its_run():
    """/tasks/reconcile-month requires runId; the body must carry it (it equals the task ID)."""
    body = json.loads(CloudTasksQueue.month_task_body("org_1", "2026-03", 4))
    assert body == {
        "orgId": "org_1",
        "month": "2026-03",
        "generation": 4,
        "runId": "month-org_1-2026-03-4",
    }


async def test_drain_returns_when_nothing_is_pending():
    await asyncio.wait_for(InlineTaskQueue().drain(), timeout=1)
