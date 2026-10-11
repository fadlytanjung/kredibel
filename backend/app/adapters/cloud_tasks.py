"""Cloud Tasks adapter for enqueuing workflow jobs to Cloud Run worker.

Normative references: docs/05 §5.2, ADR-006, AC-003-4, AC-004-4.
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from app.ports.task_queue import TaskQueue

logger = logging.getLogger(__name__)


class InlineTaskQueue(TaskQueue):
    """Local / in-process task queue for local development and offline runs."""

    def __init__(self) -> None:
        self.enqueued_document_tasks: list[dict[str, Any]] = []
        self.enqueued_month_tasks: list[dict[str, Any]] = []

    async def enqueue_document_task(
        self, org_id: str, doc_id: str, run_id: str, attempt: int = 1
    ) -> str:
        task_name = f"doc-{doc_id}-{attempt}"
        logger.info(
            "Enqueued document task inline: org=%s, doc=%s, run=%s, task=%s",
            org_id,
            doc_id,
            run_id,
            task_name,
        )
        self.enqueued_document_tasks.append(
            {
                "orgId": org_id,
                "docId": doc_id,
                "runId": run_id,
                "taskName": task_name,
                "attempt": attempt,
            }
        )
        return task_name

    async def enqueue_month_task(
        self, org_id: str, month: str, generation: int, delay_seconds: int = 20
    ) -> str:
        task_name = f"month-{org_id}-{month}-{generation}"
        logger.info(
            "Enqueued month task inline: org=%s, month=%s, gen=%d, delay=%ds",
            org_id,
            month,
            generation,
            delay_seconds,
        )
        self.enqueued_month_tasks.append(
            {
                "orgId": org_id,
                "month": month,
                "generation": generation,
                "delaySeconds": delay_seconds,
                "taskName": task_name,
            }
        )
        return task_name


class CloudTasksQueue(TaskQueue):
    """Google Cloud Tasks adapter dispatching tasks to kredibel-worker Cloud Run service."""

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
        payload = json.dumps({"orgId": org_id, "month": month, "generation": generation}).encode()

        task_id = f"month-{org_id}-{month}-{generation}"
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
