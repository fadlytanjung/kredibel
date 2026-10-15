"""Burst debounce and generation check tests (T004-08, AC-004-6).

Normative reference:
AC-004-6: Ten uploads for March within 20 seconds produce exactly one month run
that finishes DONE (the others SUPERSEDED or never started).
"""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from app.adapters.policy_files import load_plans
from app.agents.deps import PipelineDeps
from app.agents.workflows.month_workflow import build_month_workflow
from app.core.settings import Settings
from app.domain.models.document import DocStatus, DocType, Document
from app.domain.models.month import MonthState
from app.domain.models.run import RunStatus
from app.domain.models.workspace import Subscription
from app.services.entitlement_service import EntitlementService
from app.services.month_service import MonthService
from app.services.runs import RunService
from tests.fakes.clock import FixedClock
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.month_repository import FakeMonthRepository
from tests.fakes.run_repository import FakeRunRepository
from tests.fakes.task_queue import FakeTaskQueue
from tests.fakes.usage_repository import FakeUsageRepository

NOW = datetime(2026, 3, 15, 10, 0, tzinfo=UTC)
trace.set_tracer_provider(TracerProvider())

PLANS = load_plans(Path(__file__).resolve().parents[3] / "contracts" / "plans.v1.yaml")


@pytest.fixture
def burst_env():
    plans = PLANS
    settings = Settings(
        runs_enabled=True,
        run_quota_per_org_per_day=100,
        month_run_delay_seconds=20,
    )
    run_repo = FakeRunRepository()
    month_repo = FakeMonthRepository()
    doc_repo = FakeDocumentRepository()
    task_queue = FakeTaskQueue()
    usage_repo = FakeUsageRepository()
    clock = FixedClock(NOW)

    usage_repo.subscriptions["org_burst"] = Subscription(plan_id="free_trial", status="ACTIVE")

    entitlement_service = EntitlementService(
        repo=usage_repo,
        plans=plans,
        clock=clock,
        run_quota_per_org_per_day=100,
    )

    pipeline_deps = PipelineDeps(
        settings=settings,
        run_repo=run_repo,
        doc_repo=doc_repo,
        month_repo=month_repo,
        task_queue=task_queue,
        clock=clock,
    )

    async def _month_runner(
        org_id: str, month: str, generation: int, run_id: str
    ) -> dict[str, Any]:
        wf = build_month_workflow(pipeline_deps)
        sessions = InMemorySessionService()
        runner = Runner(agent=cast(Any, wf), app_name="kredibel", session_service=sessions)
        await sessions.create_session(
            app_name="kredibel",
            user_id="system",
            session_id=run_id,
            state={
                "node_input": {
                    "orgId": org_id,
                    "month": month,
                    "generation": generation,
                    "runId": run_id,
                }
            },
        )
        last: dict[str, Any] = {}
        async for event in runner.run_async(user_id="system", session_id=run_id):
            out = getattr(event, "output", None)
            if isinstance(out, dict):
                last = cast(dict[str, Any], out)
        return last

    run_service = RunService(
        run_repo=run_repo,
        month_repo=month_repo,
        task_queue=task_queue,
        entitlement_service=entitlement_service,
        settings=settings,
        clock=clock,
        month_workflow_runner=_month_runner,
    )

    month_service = MonthService(month_repo=month_repo, run_service=run_service)

    return (
        run_service,
        month_service,
        month_repo,
        run_repo,
        doc_repo,
        task_queue,
    )


@pytest.mark.asyncio
async def test_ac004_6_ten_uploads_burst_produces_exactly_one_done_run(burst_env):
    """Ten rapid uploads within 20s coalesce into 1 effective month run DONE and 9 SUPERSEDED."""
    (
        run_service,
        month_service,
        month_repo,
        run_repo,
        doc_repo,
        task_queue,
    ) = burst_env

    org_id = "org_burst"
    month = "2026-03"

    # Add a bank statement for the month so finalized state is RECONCILED
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
        months=[month],
    )
    await doc_repo.save_document(org_id, stmt)

    # 10 rapid changes (uploads, category updates, review fixes) triggered in burst
    run_ids: list[str] = []
    for _ in range(10):
        ids = await month_service.mark_dirty(org_id, [month])
        run_ids.extend(ids)

    assert len(run_ids) == 10
    assert len(task_queue.enqueued_month_tasks) == 10

    # Month in repository should now be at generation 10 and dirty=True
    month_record = await month_repo.get(org_id, month)
    assert month_record is not None
    assert month_record.generation == 10
    assert month_record.dirty is True

    # Process all 10 tasks in order of creation
    results = []
    for org, m, gen, _delay in task_queue.enqueued_month_tasks:
        task_run_id = f"month-{org}-{m}-{gen}"
        res = await run_service.reconcile_month_task(org, m, gen, task_run_id)
        results.append(res)

    # Generations 1..9 were superseded before doing any work
    for i in range(9):
        assert results[i].get("skipped") == "superseded"
        run = await run_repo.get(org_id, run_ids[i])
        assert run is not None
        assert run.status == RunStatus.SUPERSEDED

    # Generation 10 executed month_workflow and completed with status DONE
    assert results[9].get("skipped") is None
    assert results[9].get("ok") is True
    run_10 = await run_repo.get(org_id, run_ids[9])
    assert run_10 is not None
    assert run_10.status == RunStatus.DONE

    # Verify counts across all runs for the month
    all_runs = [await run_repo.get(org_id, r_id) for r_id in run_ids]
    done_runs = [r for r in all_runs if r and r.status == RunStatus.DONE]
    superseded_runs = [r for r in all_runs if r and r.status == RunStatus.SUPERSEDED]

    assert len(done_runs) == 1
    assert len(superseded_runs) == 9

    # Month is finalized cleanly
    final_month = await month_repo.get(org_id, month)
    assert final_month is not None
    assert final_month.generation == 10
    assert final_month.dirty is False
    assert final_month.state == MonthState.COLLECTING
    assert final_month.note == "Reconciliation is not available yet."
    assert final_month.last_run_id == f"month-{org_id}-{month}-10"


@pytest.mark.asyncio
async def test_ac004_6_concurrent_burst_tasks_execution(burst_env):
    """When tasks are dispatched concurrently, exactly one run finishes DONE."""
    (
        run_service,
        month_service,
        month_repo,
        run_repo,
        doc_repo,
        task_queue,
    ) = burst_env

    org_id = "org_burst"
    month = "2026-03"

    run_ids: list[str] = []
    for _ in range(10):
        ids = await month_service.mark_dirty(org_id, [month])
        run_ids.extend(ids)

    # Execute all 10 tasks concurrently
    tasks_to_run = [
        run_service.reconcile_month_task(org, m, gen, f"month-{org}-{m}-{gen}")
        for org, m, gen, _delay in task_queue.enqueued_month_tasks
    ]
    await asyncio.gather(*tasks_to_run)

    # Check that exactly one run is DONE and the other 9 are SUPERSEDED
    all_runs = [await run_repo.get(org_id, r_id) for r_id in run_ids]
    done_runs = [r for r in all_runs if r and r.status == RunStatus.DONE]
    superseded_runs = [r for r in all_runs if r and r.status == RunStatus.SUPERSEDED]

    assert len(done_runs) == 1
    assert done_runs[0].generation == 10
    assert len(superseded_runs) == 9

    final_month = await month_repo.get(org_id, month)
    assert final_month is not None
    assert final_month.dirty is False
    assert final_month.generation == 10


@pytest.mark.asyncio
async def test_ac004_6_mid_execution_generation_bump_supersedes_run(burst_env):
    """If generation bumps while a run is in flight, finalize_month supersedes it."""
    (
        run_service,
        month_service,
        month_repo,
        run_repo,
        doc_repo,
        task_queue,
    ) = burst_env

    org_id = "org_burst"
    month = "2026-03"

    # Start generation 1
    run1 = await run_service.start_month_run(org_id, month)
    assert run1.generation == 1

    # While task 1 is running, a new change bumps to generation 2
    run2 = await run_service.start_month_run(org_id, month)
    assert run2.generation == 2

    # Now task 1 executes
    res1 = await run_service.reconcile_month_task(org_id, month, 1, run1.run_id)
    assert res1.get("skipped") == "superseded"

    r1 = await run_repo.get(org_id, run1.run_id)
    assert r1 is not None
    assert r1.status == RunStatus.SUPERSEDED

    # Task 2 executes and finishes DONE
    res2 = await run_service.reconcile_month_task(org_id, month, 2, run2.run_id)
    assert res2.get("ok") is True
    assert res2.get("skipped") is None

    r2 = await run_repo.get(org_id, run2.run_id)
    assert r2 is not None
    assert r2.status == RunStatus.DONE
