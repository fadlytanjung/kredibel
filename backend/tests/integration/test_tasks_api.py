"""Integration tests for worker tasks API (T004-04, AC-004-1, AC-004-3, AC-004-5).

Covers:
- POST /tasks/process-document: success, idempotent re-delivery (200 finished), retryable 500
- POST /tasks/reconcile-month: success, idempotent re-delivery (200 finished),
  superseded (200 superseded)
- OIDC token authentication verification
- Role-based mounting isolation (web 404 vs worker 200)
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.adapters.policy_files import load_plans
from app.core.settings import Settings
from app.domain.models.month import Month, MonthState
from app.domain.models.run import RunStatus
from app.main import AppDeps, create_app
from tests.fakes.clock import FixedClock
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.identity_admin import FakeIdentityAdmin
from tests.fakes.month_repository import FakeMonthRepository
from tests.fakes.run_repository import FakeRunRepository
from tests.fakes.task_queue import FakeTaskQueue
from tests.fakes.usage_repository import FakeUsageRepository
from tests.fakes.workspace_repository import FakeWorkspaceRepository, demo_workspace

PLANS = load_plans(Path(__file__).resolve().parents[3] / "contracts" / "plans.v1.yaml")
NOW = datetime(2026, 3, 15, 10, 0, tzinfo=UTC)


class FakeTaskTokenVerifier:
    def __init__(self, valid_tokens: set[str]) -> None:
        self.valid_tokens = valid_tokens

    def verify_token(self, token: str) -> dict[str, Any]:
        if token not in self.valid_tokens:
            raise ValueError(f"Invalid token: {token}")
        return {
            "email": "kredibel-tasks-invoker@cloud-hack2skill.iam.gserviceaccount.com",
            "email_verified": True,
        }


@pytest.fixture
def base_deps():
    settings = Settings(app_role="worker")
    workspaces = FakeWorkspaceRepository()
    workspaces.workspaces["org_demo"] = demo_workspace("org_demo")
    run_repo = FakeRunRepository()
    month_repo = FakeMonthRepository()
    task_queue = FakeTaskQueue()
    clock = FixedClock(NOW)

    deps = AppDeps(
        settings,
        PLANS,
        workspace_repo=workspaces,
        usage_repo=FakeUsageRepository(workspaces=workspaces),
        identity=FakeIdentityAdmin(),
        doc_repo=FakeDocumentRepository(),
        month_repo=month_repo,
        run_repo=run_repo,
        task_queue=task_queue,
        clock=clock,
    )
    return deps, run_repo, month_repo


@pytest.mark.asyncio
async def test_ac004_3_process_document_success_and_idempotent(base_deps):
    """POST /tasks/process-document marks run DONE, re-delivery is a no-op returning finished."""
    deps, run_repo, _ = base_deps
    app = create_app(settings=Settings(app_role="worker"), deps=deps)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First call: processes document
        payload = {"orgId": "org_demo", "docId": "doc_123", "runId": "doc-doc_123-1", "attempt": 1}
        res1 = await client.post("/tasks/process-document", json=payload)
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["ok"] is True
        assert data1["skipped"] is None

        # Verify run is marked DONE in repo
        run = await run_repo.get("org_demo", "doc-doc_123-1")
        assert run is not None
        assert run.status == RunStatus.DONE

        # Second call (re-delivery of same task): idempotent no-op
        res2 = await client.post("/tasks/process-document", json=payload)
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["ok"] is True
        assert data2["skipped"] == "finished"


@pytest.mark.asyncio
async def test_ac004_3_process_document_failure_returns_500(base_deps):
    """When a node failure occurs with a retryable error, return 500 for Cloud Tasks retry."""
    deps, _, _ = base_deps

    async def failing_runner(org_id: str, doc_id: str, run_id: str, attempt: int):
        raise RuntimeError("OCR service temporarily unavailable")

    deps.run_service._document_workflow_runner = failing_runner
    app = create_app(settings=Settings(app_role="worker"), deps=deps)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"orgId": "org_demo", "docId": "doc_fail", "runId": "doc-doc_fail-1"}
        res = await client.post("/tasks/process-document", json=payload)
        assert res.status_code == 500


@pytest.mark.asyncio
async def test_ac004_5_reconcile_month_success_and_idempotent(base_deps):
    """POST /tasks/reconcile-month cleans dirty flag and marks run DONE; redelivery is no-op."""
    deps, run_repo, month_repo = base_deps
    month = Month(month="2026-03", state=MonthState.COLLECTING, dirty=True, generation=1)
    await month_repo.save("org_demo", month)

    app = create_app(settings=Settings(app_role="worker"), deps=deps)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "orgId": "org_demo",
            "month": "2026-03",
            "generation": 1,
            "runId": "month-org_demo-2026-03-1",
        }
        res1 = await client.post("/tasks/reconcile-month", json=payload)
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["ok"] is True
        assert data1["skipped"] is None

        # Verify month is now clean and run is DONE
        updated_month = await month_repo.get("org_demo", "2026-03")
        assert updated_month is not None
        assert updated_month.dirty is False
        assert updated_month.last_run_id == "month-org_demo-2026-03-1"

        run = await run_repo.get("org_demo", "month-org_demo-2026-03-1")
        assert run is not None
        assert run.status == RunStatus.DONE

        # Re-delivery of same task: idempotent no-op
        res2 = await client.post("/tasks/reconcile-month", json=payload)
        assert res2.status_code == 200
        assert res2.json()["skipped"] == "finished"


@pytest.mark.asyncio
async def test_ac004_5_reconcile_month_superseded_when_older_generation(base_deps):
    """If month generation was bumped to 2, task with generation 1 ends SUPERSEDED."""
    deps, run_repo, month_repo = base_deps
    # Month already at generation 2
    month = Month(month="2026-03", state=MonthState.COLLECTING, dirty=True, generation=2)
    await month_repo.save("org_demo", month)

    app = create_app(settings=Settings(app_role="worker"), deps=deps)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "orgId": "org_demo",
            "month": "2026-03",
            "generation": 1,
            "runId": "month-org_demo-2026-03-1",
        }
        res = await client.post("/tasks/reconcile-month", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["skipped"] == "superseded"

        # Month should remain dirty at gen 2
        m = await month_repo.get("org_demo", "2026-03")
        assert m is not None
        assert m.dirty is True
        assert m.generation == 2

        # Run in repo is SUPERSEDED
        run = await run_repo.get("org_demo", "month-org_demo-2026-03-1")
        assert run is not None
        assert run.status == RunStatus.SUPERSEDED


@pytest.mark.asyncio
async def test_ac004_1_oidc_auth_enforced_when_configured(base_deps):
    """Task endpoints require valid OIDC token when task authentication is configured."""
    deps, _, _ = base_deps
    verifier = FakeTaskTokenVerifier(valid_tokens={"valid-tasks-oidc-token"})
    app = create_app(
        settings=Settings(app_role="worker"),
        deps=deps,
        task_token_verifier=verifier,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"orgId": "org_demo", "docId": "doc_1", "runId": "doc-doc_1-1"}

        # Missing token -> 401
        res_no_token = await client.post("/tasks/process-document", json=payload)
        assert res_no_token.status_code == 401

        # Invalid token -> 401
        res_bad_token = await client.post(
            "/tasks/process-document",
            json=payload,
            headers={"Authorization": "Bearer bad-token"},
        )
        assert res_bad_token.status_code == 401

        # Valid token -> 200
        res_ok = await client.post(
            "/tasks/process-document",
            json=payload,
            headers={"Authorization": "Bearer valid-tasks-oidc-token"},
        )
        assert res_ok.status_code == 200
        assert res_ok.json()["ok"] is True


@pytest.mark.asyncio
async def test_ac001_10_tasks_not_mounted_on_web_role(base_deps):
    """Worker task endpoints return 404 on web role and 200 on worker role."""
    deps, _, _ = base_deps
    web_app = create_app(settings=Settings(app_role="web"), deps=deps)

    transport = ASGITransport(app=web_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/tasks/process-document",
            json={"orgId": "org_demo", "docId": "doc_1", "runId": "doc-doc_1-1"},
        )
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_the_last_cloud_tasks_attempt_marks_the_document_failed(base_deps):
    """Cloud Tasks resends the same body; its retry header says which attempt this is. A document
    whose third attempt fails is FAILED, not left UPLOADED (found in production)."""
    from app.domain.models.document import Document

    deps, _, _ = base_deps
    seen: list[int] = []

    async def failing_runner(org_id: str, doc_id: str, run_id: str, attempt: int):
        seen.append(attempt)
        raise RuntimeError("worker misconfigured")

    deps.run_service._document_workflow_runner = failing_runner
    doc_id = "doc_stuck"
    await deps.doc_repo.save_document(
        "org_demo",
        Document(
            doc_id=doc_id,
            file_name="s.pdf",
            content_type="application/pdf",
            size_bytes=1,
            page_count=1,
            sha256="0" * 64,
            gcs_path=f"orgs/org_demo/documents/{doc_id}/original.pdf",
            uploaded_by="u-1",
            uploaded_at=NOW,
        ),
    )
    app = create_app(settings=Settings(app_role="worker"), deps=deps)
    payload = {"orgId": "org_demo", "docId": doc_id, "runId": "run_x", "attempt": 1}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for retry in ("0", "1"):
            res = await client.post(
                "/tasks/process-document",
                json=payload,
                headers={"X-CloudTasks-TaskRetryCount": retry},
            )
            assert res.status_code == 500
            assert (await deps.doc_repo.get_document("org_demo", doc_id)).status.value == "UPLOADED"
        res = await client.post(
            "/tasks/process-document", json=payload, headers={"X-CloudTasks-TaskRetryCount": "2"}
        )
    assert res.status_code == 500
    assert seen == [1, 2, 3]
    doc = await deps.doc_repo.get_document("org_demo", doc_id)
    assert (doc.status.value, doc.status_detail) == ("FAILED", "E02_EXTRACTION_FAILED")
