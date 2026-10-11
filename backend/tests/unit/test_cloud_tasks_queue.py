"""Unit tests for CloudTasksQueue and InlineTaskQueue adapters (Spec 004 T004-03, AC-004-4)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.adapters.cloud_tasks_queue import CloudTasksQueue, InlineTaskQueue


@pytest.mark.asyncio
async def test_inline_task_queue_document_and_month():
    queue = InlineTaskQueue()

    doc_task = await queue.enqueue_document_task("org_1", "doc_1", "run_1", attempt=2)
    assert doc_task == "doc-doc_1-2"
    assert len(queue.enqueued_document_tasks) == 1
    assert queue.enqueued_document_tasks[0]["taskName"] == "doc-doc_1-2"

    month_task = await queue.enqueue_month_task("org_1", "2026-03", generation=5, delay_seconds=20)
    assert month_task == "month-org_1-2026-03-5"
    assert len(queue.enqueued_month_tasks) == 1
    assert queue.enqueued_month_tasks[0]["taskName"] == "month-org_1-2026-03-5"
    assert queue.enqueued_month_tasks[0]["delaySeconds"] == 20


@pytest.mark.asyncio
async def test_cloud_tasks_queue_enqueues_document_task():
    queue = CloudTasksQueue(
        project_id="test-proj",
        location="asia-southeast1",
        document_queue="kredibel-documents",
        month_queue="kredibel-months",
        invoker_service_account="invoker@test.iam.gserviceaccount.com",
        worker_base_url="https://worker.kredibel.internal",
    )

    mock_client = MagicMock()
    queue_path = "projects/test-proj/locations/asia-southeast1/queues/kredibel-documents"
    mock_client.queue_path.return_value = queue_path
    mock_created = MagicMock()
    mock_created.name = f"{queue_path}/tasks/doc-doc_1-1"
    mock_client.create_task.return_value = mock_created

    with patch.object(queue, "_get_client", return_value=mock_client):
        task_name = await queue.enqueue_document_task("org_1", "doc_1", "run_1", attempt=1)

    assert task_name == mock_created.name
    mock_client.create_task.assert_called_once()
    _, kwargs = mock_client.create_task.call_args
    task_arg = kwargs["task"]
    assert task_arg.name == f"{queue_path}/tasks/doc-doc_1-1"
    assert task_arg.http_request.url == "https://worker.kredibel.internal/tasks/process-document"
    payload = json.loads(task_arg.http_request.body.decode())
    assert payload == {"orgId": "org_1", "docId": "doc_1", "runId": "run_1", "attempt": 1}
    assert (
        task_arg.http_request.oidc_token.service_account_email
        == "invoker@test.iam.gserviceaccount.com"
    )


@pytest.mark.asyncio
async def test_cloud_tasks_queue_enqueues_month_task_with_delay():
    queue = CloudTasksQueue(
        project_id="test-proj",
        location="asia-southeast1",
        document_queue="kredibel-documents",
        month_queue="kredibel-months",
        invoker_service_account="invoker@test.iam.gserviceaccount.com",
        worker_base_url="https://worker.kredibel.internal",
    )

    mock_client = MagicMock()
    queue_path = "projects/test-proj/locations/asia-southeast1/queues/kredibel-months"
    mock_client.queue_path.return_value = queue_path
    mock_created = MagicMock()
    mock_created.name = f"{queue_path}/tasks/month-org_1-2026-03-3"
    mock_client.create_task.return_value = mock_created

    with patch.object(queue, "_get_client", return_value=mock_client):
        task_name = await queue.enqueue_month_task(
            "org_1", "2026-03", generation=3, delay_seconds=20
        )

    assert task_name == mock_created.name
    mock_client.create_task.assert_called_once()
    _, kwargs = mock_client.create_task.call_args
    task_arg = kwargs["task"]
    assert task_arg.name == f"{queue_path}/tasks/month-org_1-2026-03-3"
    assert task_arg.http_request.url == "https://worker.kredibel.internal/tasks/reconcile-month"
    assert task_arg.schedule_time is not None
    payload = json.loads(task_arg.http_request.body.decode())
    assert payload == {"orgId": "org_1", "month": "2026-03", "generation": 3}
