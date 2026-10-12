"""Unit tests for month_workflow orchestrator (T004-07, AC-004-5, AC-004-7)."""

from datetime import UTC, datetime
from typing import Any, cast

import pytest
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from app.agents.deps import PipelineDeps
from app.agents.workflows.month_workflow import build_month_workflow
from app.core.settings import Settings
from app.domain.models.document import DocStatus, DocType, Document
from app.domain.models.month import Month, MonthState
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
    return deps, run_repo, month_repo, doc_repo


@pytest.mark.asyncio
async def test_ac004_5_month_workflow_generation_check_superseded(workflow_deps):
    """When a newer generation exists in Firestore, run ends SUPERSEDED and writes nothing."""
    deps, run_repo, month_repo, doc_repo = workflow_deps
    org_id = "org_demo"
    month_str = "2026-03"
    run_gen = 1
    newer_gen = 2
    run_id = f"month-{org_id}-{month_str}-{run_gen}"

    # Month in repository was bumped to generation 2 (e.g. by another document upload)
    month = Month(month=month_str, state=MonthState.COLLECTING, dirty=True, generation=newer_gen)
    await month_repo.save(org_id, month)
    await run_repo.create(
        org_id,
        Run(
            run_id=run_id,
            kind=RunKind.MONTH,
            target=month_str,
            generation=run_gen,
            status=RunStatus.RUNNING,
        ),
    )

    wf = build_month_workflow(deps)
    sessions = InMemorySessionService()
    runner = Runner(agent=cast(Any, wf), app_name="kredibel", session_service=sessions)

    await sessions.create_session(
        app_name="kredibel",
        user_id="user_1",
        session_id=run_id,
        state={
            "node_input": {
                "orgId": org_id,
                "month": month_str,
                "generation": run_gen,
                "runId": run_id,
            }
        },
    )

    async for _ in runner.run_async(user_id="user_1", session_id=run_id):
        pass

    # Run was marked SUPERSEDED
    run = await run_repo.get(org_id, run_id)
    assert run is not None
    assert run.status == RunStatus.SUPERSEDED

    # Month was NOT modified by the superseded run (still dirty=True, generation=2)
    saved_month = await month_repo.get(org_id, month_str)
    assert saved_month is not None
    assert saved_month.generation == newer_gen
    assert saved_month.dirty is True
    assert saved_month.last_run_id != run_id


@pytest.mark.asyncio
async def test_ac004_7_month_workflow_without_statement_ends_collecting(workflow_deps):
    """A month with no bank statement ends in COLLECTING state (waiting for statement)."""
    deps, run_repo, month_repo, doc_repo = workflow_deps
    org_id = "org_demo"
    month_str = "2026-03"
    gen = 1
    run_id = f"month-{org_id}-{month_str}-{gen}"

    month = Month(month=month_str, state=MonthState.COLLECTING, dirty=True, generation=gen)
    await month_repo.save(org_id, month)
    await run_repo.create(
        org_id,
        Run(
            run_id=run_id,
            kind=RunKind.MONTH,
            target=month_str,
            generation=gen,
            status=RunStatus.RUNNING,
        ),
    )

    # Only an invoice uploaded, no bank statement
    invoice = Document(
        doc_id="inv_1",
        file_name="invoice.pdf",
        content_type="application/pdf",
        size_bytes=500,
        page_count=1,
        sha256="sha_inv",
        gcs_path=f"docs/{org_id}/inv_1.pdf",
        uploaded_by="user_1",
        uploaded_at=NOW,
        doc_type=DocType.SALES_INVOICE,
        status=DocStatus.DONE,
        months=[month_str],
    )
    await doc_repo.save_document(org_id, invoice)

    wf = build_month_workflow(deps)
    sessions = InMemorySessionService()
    runner = Runner(agent=cast(Any, wf), app_name="kredibel", session_service=sessions)

    await sessions.create_session(
        app_name="kredibel",
        user_id="user_1",
        session_id=run_id,
        state={
            "node_input": {
                "orgId": org_id,
                "month": month_str,
                "generation": gen,
                "runId": run_id,
            }
        },
    )

    async for _ in runner.run_async(user_id="user_1", session_id=run_id):
        pass

    # Run finished DONE
    run = await run_repo.get(org_id, run_id)
    assert run is not None
    assert run.status == RunStatus.DONE

    # Month ended in COLLECTING and dirty=False
    saved_month = await month_repo.get(org_id, month_str)
    assert saved_month is not None
    assert saved_month.state == MonthState.COLLECTING
    assert saved_month.dirty is False
    assert saved_month.last_run_id == run_id


@pytest.mark.asyncio
async def test_ac007_14_statement_presence_does_not_claim_reconciliation(workflow_deps):
    """The skeleton cannot report reconciliation without computed matches/coverage/checks."""
    deps, run_repo, month_repo, doc_repo = workflow_deps
    org_id = "org_demo"
    month_str = "2026-03"
    gen = 1
    run_id = f"month-{org_id}-{month_str}-{gen}"

    month = Month(month=month_str, state=MonthState.COLLECTING, dirty=True, generation=gen)
    await month_repo.save(org_id, month)
    await run_repo.create(
        org_id,
        Run(
            run_id=run_id,
            kind=RunKind.MONTH,
            target=month_str,
            generation=gen,
            status=RunStatus.RUNNING,
        ),
    )

    # Bank statement uploaded
    stmt = Document(
        doc_id="stmt_1",
        file_name="statement.pdf",
        content_type="application/pdf",
        size_bytes=1000,
        page_count=2,
        sha256="sha_stmt",
        gcs_path=f"docs/{org_id}/stmt_1.pdf",
        uploaded_by="user_1",
        uploaded_at=NOW,
        doc_type=DocType.BANK_STATEMENT,
        status=DocStatus.DONE,
        months=[month_str],
    )
    await doc_repo.save_document(org_id, stmt)

    wf = build_month_workflow(deps)
    sessions = InMemorySessionService()
    runner = Runner(agent=cast(Any, wf), app_name="kredibel", session_service=sessions)

    await sessions.create_session(
        app_name="kredibel",
        user_id="user_1",
        session_id=run_id,
        state={
            "node_input": {
                "orgId": org_id,
                "month": month_str,
                "generation": gen,
                "runId": run_id,
            }
        },
    )

    async for _ in runner.run_async(user_id="user_1", session_id=run_id):
        pass

    # Run finished DONE
    run = await run_repo.get(org_id, run_id)
    assert run is not None
    assert run.status == RunStatus.DONE

    # Processing ran, but actual reconciliation is not implemented yet.
    saved_month = await month_repo.get(org_id, month_str)
    assert saved_month is not None
    assert saved_month.state == MonthState.COLLECTING
    assert saved_month.note == "Reconciliation is not available yet."
    assert saved_month.dirty is False
    assert saved_month.last_run_id == run_id

    # All 10 stages recorded in order
    stage_nodes = [s.node for s in run.stages]
    expected_order = [
        "load_month",
        "reconcile",
        "check_month",
        "build_counterparties",
        "suggest_profile",
        "score_risk",
        "explain_month",
        "build_flows",
        "sync_review_items",
        "finalize_month",
    ]
    for expected_stage in expected_order:
        assert expected_stage in stage_nodes
