"""Cloud Tasks adapter for enqueuing workflow jobs to Cloud Run worker.

Normative references: docs/05 §5.2, ADR-006, AC-003-4, AC-004-4.
"""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable, Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any

from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from app.ports.task_queue import TaskQueue

logger = logging.getLogger(__name__)


DocumentHandler = Callable[[str, str, str, int], Awaitable[Any]]
MonthHandler = Callable[[str, str, int, str], Awaitable[Any]]
MAX_ATTEMPTS = 3  # as the document queue's retry policy (docs/16 §3); the third failure is E02


def month_task_id(org_id: str, month: str, generation: int) -> str:
    """The month task's name, which is also its run ID (AC-004-4)."""
    return f"month-{org_id}-{month}-{generation}"


class InlineTaskQueue(TaskQueue):
    """Local development runs the worker in-process (docs/13 §7, docs/16 §1): each task calls its
    handler as a background asyncio task, with the delay and retries Cloud Tasks would apply.
    Without handlers (unit tests), tasks are only recorded."""

    def __init__(
        self,
        on_document: DocumentHandler | None = None,
        on_month: MonthHandler | None = None,
        *,
        retry_delay_seconds: float = 2.0,
    ) -> None:
        self.enqueued_document_tasks: list[dict[str, Any]] = []
        self.enqueued_month_tasks: list[dict[str, Any]] = []
        self._on_document = on_document
        self._on_month = on_month
        self._retry_delay = retry_delay_seconds
        self._pending: set[asyncio.Task[None]] = set()

    def _spawn(self, coro: Coroutine[Any, Any, None]) -> None:
        task = asyncio.get_running_loop().create_task(coro)
        self._pending.add(task)
        task.add_done_callback(self._pending.discard)

    async def drain(self) -> None:
        """Wait for every task started so far, retries included (tests and shutdown)."""
        while self._pending:
            await asyncio.gather(*list(self._pending), return_exceptions=True)

    async def enqueue_document_task(
        self, org_id: str, doc_id: str, run_id: str, attempt: int = 1
    ) -> str:
        task_name = f"doc-{doc_id}-{attempt}"
        logger.info("Enqueued document task inline: org=%s, doc=%s, run=%s", org_id, doc_id, run_id)
        self.enqueued_document_tasks.append(
            {
                "orgId": org_id,
                "docId": doc_id,
                "runId": run_id,
                "taskName": task_name,
                "attempt": attempt,
            }
        )
        if self._on_document is not None:
            self._spawn(self._run_document(org_id, doc_id, run_id, attempt))
        return task_name

    async def _run_document(self, org_id: str, doc_id: str, run_id: str, attempt: int) -> None:
        assert self._on_document is not None
        for current in range(attempt, MAX_ATTEMPTS + 1):
            try:
                await self._on_document(org_id, doc_id, run_id, current)
                return
            except Exception:
                logger.exception("Inline document task failed: doc=%s, attempt=%d", doc_id, current)
                if current < MAX_ATTEMPTS:
                    await asyncio.sleep(self._retry_delay * current)

    async def enqueue_month_task(
        self, org_id: str, month: str, generation: int, delay_seconds: int = 20
    ) -> str:
        task_name = month_task_id(org_id, month, generation)
        logger.info("Enqueued month task inline: %s, delay=%ds", task_name, delay_seconds)
        self.enqueued_month_tasks.append(
            {
                "orgId": org_id,
                "month": month,
                "generation": generation,
                "delaySeconds": delay_seconds,
                "taskName": task_name,
            }
        )
        if self._on_month is not None:
            self._spawn(self._run_month(org_id, month, generation, task_name, delay_seconds))
        return task_name

    async def _run_month(
        self, org_id: str, month: str, generation: int, run_id: str, delay_seconds: int
    ) -> None:
        assert self._on_month is not None
        await asyncio.sleep(delay_seconds)
        try:
            await self._on_month(org_id, month, generation, run_id)
        except Exception:
            logger.exception("Inline month task failed: %s", run_id)


class CloudTasksQueue(TaskQueue):
    """Google Cloud Tasks adapter dispatching tasks to kredibel-worker Cloud Run service."""

    @staticmethod
    def month_task_body(org_id: str, month: str, generation: int) -> bytes:
        """/tasks/reconcile-month requires the run ID, which is the task ID."""
        run_id = month_task_id(org_id, month, generation)
        body = {"orgId": org_id, "month": month, "generation": generation, "runId": run_id}
        return json.dumps(body).encode()

    def __init__(
        self,
        project_id: str,
        location: str,
        document_queue: str,
        month_queue: str,
        invoker_service_account: str,
        worker_base_url: str = "",
    ) -> None:
        self._project_id = project_id
        self._location = location
        self._document_queue = document_queue
        self._month_queue = month_queue
        self._invoker_sa = invoker_service_account
        self._worker_base_url = worker_base_url
        self._client: tasks_v2.CloudTasksClient | None = None

    def _get_client(self) -> tasks_v2.CloudTasksClient:
        if self._client is None:
            self._client = tasks_v2.CloudTasksClient()
        return self._client

    async def enqueue_document_task(
        self, org_id: str, doc_id: str, run_id: str, attempt: int = 1
    ) -> str:
        client = self._get_client()
        parent = client.queue_path(self._project_id, self._location, self._document_queue)
        url = (
            f"{self._worker_base_url}/tasks/process-document"
            if self._worker_base_url
            else "/tasks/process-document"
        )
        payload = json.dumps(
            {"orgId": org_id, "docId": doc_id, "runId": run_id, "attempt": attempt}
        ).encode()

        task_id = f"doc-{doc_id}-{attempt}"
        task_name = f"{parent}/tasks/{task_id}"

        task = tasks_v2.Task(
            name=task_name,
            http_request=tasks_v2.HttpRequest(
                http_method=tasks_v2.HttpMethod.POST,
                url=url,
                headers={"Content-Type": "application/json"},
                body=payload,
                oidc_token=tasks_v2.OidcToken(
                    service_account_email=self._invoker_sa,
                    audience=self._worker_base_url or url,
                )
                if self._invoker_sa
                else None,
            ),
        )
        try:
            created = client.create_task(parent=parent, task=task)
            return str(created.name) if created.name else task_id
        except Exception as e:
            logger.warning("Document task create encountered %s, returning task_id %s", e, task_id)
            return task_id

    async def enqueue_month_task(
        self, org_id: str, month: str, generation: int, delay_seconds: int = 20
    ) -> str:
        client = self._get_client()
        parent = client.queue_path(self._project_id, self._location, self._month_queue)
        url = (
            f"{self._worker_base_url}/tasks/reconcile-month"
            if self._worker_base_url
            else "/tasks/reconcile-month"
        )
        payload = self.month_task_body(org_id, month, generation)
        task_id = month_task_id(org_id, month, generation)
        task_name = f"{parent}/tasks/{task_id}"

        schedule_time = timestamp_pb2.Timestamp()
        schedule_time.FromDatetime(datetime.now(UTC) + timedelta(seconds=delay_seconds))

        task = tasks_v2.Task(
            name=task_name,
            schedule_time=schedule_time,
            http_request=tasks_v2.HttpRequest(
                http_method=tasks_v2.HttpMethod.POST,
                url=url,
                headers={"Content-Type": "application/json"},
                body=payload,
                oidc_token=tasks_v2.OidcToken(
                    service_account_email=self._invoker_sa,
                    audience=self._worker_base_url or url,
                )
                if self._invoker_sa
                else None,
            ),
        )
        try:
            created = client.create_task(parent=parent, task=task)
            return str(created.name) if created.name else task_id
        except Exception as e:
            logger.warning("Month task create encountered %s, returning task_id %s", e, task_id)
            return task_id
