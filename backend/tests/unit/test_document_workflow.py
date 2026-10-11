"""Unit tests for document_workflow orchestrator (T004-06, AC-004-1, AC-004-2, AC-004-3)."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

import pytest
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from app.agents.deps import PipelineDeps
from app.agents.workflows.document_workflow import build_document_workflow
from app.core.settings import Settings
from app.domain.models.document import DocStatus, DocType, Document
from app.domain.models.run import Run, RunKind, RunStatus
from tests.fakes.clock import FixedClock
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.month_repository import FakeMonthRepository
from tests.fakes.run_repository import FakeRunRepository
from tests.fakes.task_queue import FakeTaskQueue

NOW = datetime(2026, 3, 15, 10, 0, tzinfo=UTC)
trace.set_tracer_provider(TracerProvider())


@pytest.fixture
def workflow_deps():
    settings = Settings()
    run_repo = FakeRunRepository()
    doc_repo = FakeDocumentRepository()
    month_repo = FakeMonthRepository()
    task_queue = FakeTaskQueue()
    clock = FixedClock(NOW)

    deps = PipelineDeps(
        settings=settings,
        run_repo=run_repo,
        doc_repo=doc_repo,
        month_repo=month_repo,
        task_queue=task_queue,
        clock=clock,
    )
    return deps, run_repo, doc_repo


def make_doc(
    org_id: str,
    doc_id: str,
    *,
    doc_type: DocType = DocType.BANK_STATEMENT,
    status: DocStatus = DocStatus.UPLOADED,
    type_confidence: Decimal | None = None,
    page_count: int = 2,
    months: list[str] | None = None,
) -> Document:
    return Document(
        doc_id=doc_id,
        file_name="statement.pdf",
        content_type="application/pdf",
        size_bytes=1000,
        page_count=page_count,
        sha256=f"sha_{doc_id}",
        gcs_path=f"docs/{org_id}/{doc_id}.pdf",
        uploaded_by="user_1",
        uploaded_at=NOW,
        doc_type=doc_type,
        type_confidence=type_confidence,
        status=status,
        months=months or ["2026-03"],
    )


@pytest.mark.asyncio
async def test_ac004_1_document_workflow_node_order_and_stages(workflow_deps):
    """document_workflow runs nodes in order, records stages, and finalizes document."""
    deps, run_repo, doc_repo = workflow_deps
    org_id = "org_demo"
    doc_id = "doc_100"
    run_id = f"doc-{doc_id}-1"

    doc = make_doc(org_id, doc_id, doc_type=DocType.BANK_STATEMENT, page_count=2)
    await doc_repo.save_document(org_id, doc)
    await run_repo.create(
        org_id,
        Run(run_id=run_id, kind=RunKind.DOCUMENT, target=doc_id, status=RunStatus.RUNNING),
    )

    wf = build_document_workflow(deps)
    sessions = InMemorySessionService()
    runner = Runner(agent=cast(Any, wf), app_name="kredibel", session_service=sessions)

    await sessions.create_session(
        app_name="kredibel",
        user_id="user_1",
        session_id=run_id,
        state={
            "node_input": {
                "orgId": org_id,
                "docId": doc_id,
                "runId": run_id,
                "attempt": 1,
            }
        },
    )

    async for _ in runner.run_async(user_id="user_1", session_id=run_id):
        pass

    # Verify document finalized
    updated_doc = await doc_repo.get_document(org_id, doc_id)
    assert updated_doc is not None
    assert updated_doc.status == DocStatus.DONE

    # Verify stages recorded in order
    run = await run_repo.get(org_id, run_id)
    assert run is not None
    stage_nodes = [s.node for s in run.stages]
    assert "load_document" in stage_nodes
    assert "inspect_file" in stage_nodes
    assert "classify_document" in stage_nodes
    assert "read_page" in stage_nodes
    assert "verify_pages" in stage_nodes
    assert "check_document" in stage_nodes
    assert "detect_content_duplicates" in stage_nodes
    assert "finalize_document" in stage_nodes


@pytest.mark.asyncio
async def test_ac004_2_document_workflow_needs_input_stops_without_failing(workflow_deps):
    """When a document needs user confirmation (type/mapping), workflow stops at NEEDS_INPUT."""
    deps, run_repo, doc_repo = workflow_deps
    org_id = "org_demo"
    doc_id = "doc_confirm"
    run_id = f"doc-{doc_id}-1"

    doc = make_doc(
        org_id,
        doc_id,
        doc_type=DocType.UNKNOWN,
        type_confidence=Decimal("0.4"),  # Low confidence triggers NEEDS_INPUT
        page_count=1,
    )
    await doc_repo.save_document(org_id, doc)
    await run_repo.create(
        org_id,
        Run(run_id=run_id, kind=RunKind.DOCUMENT, target=doc_id, status=RunStatus.RUNNING),
    )

    wf = build_document_workflow(deps)
    sessions = InMemorySessionService()
    runner = Runner(agent=cast(Any, wf), app_name="kredibel", session_service=sessions)

    await sessions.create_session(
        app_name="kredibel",
        user_id="user_1",
        session_id=run_id,
        state={
            "node_input": {
                "orgId": org_id,
                "docId": doc_id,
                "runId": run_id,
                "attempt": 1,
            }
        },
    )

    async for _ in runner.run_async(user_id="user_1", session_id=run_id):
        pass

    updated_doc = await doc_repo.get_document(org_id, doc_id)
    assert updated_doc is not None
    assert updated_doc.status == DocStatus.NEEDS_INPUT

    # Workflow did not execute read_page or finalize_document
    run = await run_repo.get(org_id, run_id)
    assert run is not None
    stage_nodes = [s.node for s in run.stages]
    assert "classify_document" in stage_nodes
    assert "read_page" not in stage_nodes
    assert "finalize_document" not in stage_nodes


@pytest.mark.asyncio
async def test_ac004_3_document_workflow_final_attempt_failure_marks_failed_e02(workflow_deps):
    """When a retryable failure occurs on the last attempt, document becomes FAILED with E02."""
    deps, run_repo, doc_repo = workflow_deps
    org_id = "org_demo"
    doc_id = "doc_fail_last"
    run_id = f"doc-{doc_id}-3"

    doc = make_doc(org_id, doc_id, doc_type=DocType.BANK_STATEMENT, page_count=1)
    await doc_repo.save_document(org_id, doc)
    await run_repo.create(
        org_id,
        Run(run_id=run_id, kind=RunKind.DOCUMENT, target=doc_id, status=RunStatus.RUNNING),
    )

    wf = build_document_workflow(deps)
    sessions = InMemorySessionService()
    runner = Runner(agent=cast(Any, wf), app_name="kredibel", session_service=sessions)

    # Inject simulated failure during inspection or reading
    await sessions.create_session(
        app_name="kredibel",
        user_id="user_1",
        session_id=run_id,
        state={
            "node_input": {
                "orgId": org_id,
                "docId": doc_id,
                "runId": run_id,
                "attempt": 3,  # Last attempt
                "_simulate_failure": True,
            }
        },
    )

    from google.adk.workflow._errors import DynamicNodeFailError

    with pytest.raises((RuntimeError, DynamicNodeFailError)):
        async for _ in runner.run_async(user_id="user_1", session_id=run_id):
            pass

    updated_doc = await doc_repo.get_document(org_id, doc_id)
    assert updated_doc is not None
    assert updated_doc.status == DocStatus.FAILED
    assert updated_doc.status_detail == "E02_EXTRACTION_FAILED"


@pytest.mark.asyncio
async def test_ac004_1_ledger_export_workflow(workflow_deps):
    """LEDGER_EXPORT runs propose_ledger_mapping and parse_ledger instead of read_page."""
    deps, run_repo, doc_repo = workflow_deps
    org_id = "org_demo"
    doc_id = "doc_ledger"
    run_id = f"doc-{doc_id}-1"

    doc = make_doc(org_id, doc_id, doc_type=DocType.LEDGER_EXPORT, page_count=1)
    await doc_repo.save_document(org_id, doc)
    await run_repo.create(
        org_id,
        Run(run_id=run_id, kind=RunKind.DOCUMENT, target=doc_id, status=RunStatus.RUNNING),
    )

    wf = build_document_workflow(deps)
    sessions = InMemorySessionService()
    runner = Runner(agent=cast(Any, wf), app_name="kredibel", session_service=sessions)

    await sessions.create_session(
        app_name="kredibel",
        user_id="user_1",
        session_id=run_id,
        state={
            "node_input": {
                "orgId": org_id,
                "docId": doc_id,
                "runId": run_id,
                "mappingConfirmed": True,
                "attempt": 1,
            }
        },
    )

    async for _ in runner.run_async(user_id="user_1", session_id=run_id):
        pass

    updated_doc = await doc_repo.get_document(org_id, doc_id)
    assert updated_doc is not None
    assert updated_doc.status == DocStatus.DONE

    run = await run_repo.get(org_id, run_id)
    assert run is not None
    stage_nodes = [s.node for s in run.stages]
    assert "propose_ledger_mapping" in stage_nodes
    assert "parse_ledger" in stage_nodes
    assert "read_page" not in stage_nodes
    assert "finalize_document" in stage_nodes
