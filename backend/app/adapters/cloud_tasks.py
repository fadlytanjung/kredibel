"""Cloud Tasks adapter for enqueuing document and month workflow runs (docs/06 §2).

Normative references: docs/06 §2, docs/10 §2.9, ADR-008.
"""

import json
import logging
from typing import Any

from google.cloud import tasks_v2

from app.ports.task_queue import TaskQueue

logger = logging.getLogger(__name__)


class InlineTaskQueue(TaskQueue):
    """Local / in-process task queue for local development and offline runs."""

    def __init__(self) -> None:
        self.enqueued_document_tasks: list[dict[str, str]] = []
        self.enqueued_month_tasks: list[dict[str, Any]] = []

    async def enqueue_document_task(self, org_id: str, doc_id: str, run_id: str) -> str:
        task_name = f"doc-{doc_id}-1"
        logger.info(
            "Enqueued document task inline: org=%s, doc=%s, run=%s, task=%s",
            org_id,
            doc_id,
            run_id,
            task_name,
        )
        self.enqueued_document_tasks.append(
            {"orgId": org_id, "docId": doc_id, "runId": run_id, "taskName": task_name}
        )
        return task_name

    async def enqueue_month_task(
        self, org_id: str, month: str, generation: int, run_id: str
    ) -> None:
        logger.info(
            "Enqueued month task inline: org=%s, month=%s, gen=%d, run=%s",
            org_id,
            month,
            generation,
            run_id,
        )
        self.enqueued_month_tasks.append(
            {"orgId": org_id, "month": month, "generation": generation, "runId": run_id}
        )


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

    async def enqueue_document_task(self, org_id: str, doc_id: str, run_id: str) -> str:
        client = self._get_client()
        parent = client.queue_path(self._project_id, self._location, self._document_queue)
        url = (
            f"{self._worker_base_url}/tasks/process-document"
            if self._worker_base_url
            else "/tasks/process-document"
        )
        payload = json.dumps({"orgId": org_id, "docId": doc_id, "runId": run_id}).encode()

        task = tasks_v2.Task(
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
            )
        )
        created = client.create_task(parent=parent, task=task)
        return str(created.name) if created.name else f"doc-{doc_id}-1"

    async def enqueue_month_task(
        self, org_id: str, month: str, generation: int, run_id: str
    ) -> None:
        client = self._get_client()
        parent = client.queue_path(self._project_id, self._location, self._month_queue)
        url = (
            f"{self._worker_base_url}/tasks/process-month"
            if self._worker_base_url
            else "/tasks/process-month"
        )
        payload = json.dumps(
            {"orgId": org_id, "month": month, "generation": generation, "runId": run_id}
        ).encode()

        task = tasks_v2.Task(
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
            )
        )
        client.create_task(parent=parent, task=task)
