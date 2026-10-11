"""Tests for RunService and MonthService (Spec 004 AC-004-4, AC-004-10, AC-004-11).

TDD tests verifying:
- generation bump and deterministic task name in one transaction
- 20-second debounce delay
- runs_enabled check (RUNS_DISABLED error)
- user requested runs quota check (RUN_QUOTA_EXCEEDED error)
- automatic runs exceeding quota delayed with note
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.adapters.policy_files import load_plans
from app.core.settings import Settings
from app.domain.errors import RunQuotaExceededError, RunsDisabledError
from app.domain.models.run import RunKind, RunStatus
from app.domain.models.workspace import Subscription, UsageDay
from app.services.entitlement_service import EntitlementService
from app.services.runs import RunService
from tests.fakes.clock import FixedClock
from tests.fakes.month_repository import FakeMonthRepository
from tests.fakes.run_repository import FakeRunRepository
from tests.fakes.task_queue import FakeTaskQueue
from tests.fakes.usage_repository import FakeUsageRepository

PLANS = load_plans(Path(__file__).resolve().parents[3] / "contracts" / "plans.v1.yaml")


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(datetime(2026, 3, 15, 10, 0, 0, tzinfo=UTC))


@pytest.fixture
def month_repo() -> FakeMonthRepository:
    return FakeMonthRepository()


@pytest.fixture
def run_repo() -> FakeRunRepository:
    return FakeRunRepository()


@pytest.fixture
def task_queue() -> FakeTaskQueue:
    return FakeTaskQueue()


@pytest.fixture
def usage_repo() -> FakeUsageRepository:
    repo = FakeUsageRepository()
    repo.subscriptions["org_test"] = Subscription(plan_id="free_trial", status="ACTIVE")
    return repo


@pytest.fixture
def entitlement_service(usage_repo: FakeUsageRepository, clock: FixedClock) -> EntitlementService:
    return EntitlementService(
        repo=usage_repo,
        plans=PLANS,
        clock=clock,
        run_quota_per_org_per_day=80,
    )


@pytest.fixture
def settings() -> Settings:
    return Settings(
        runs_enabled=True,
        run_quota_per_org_per_day=80,
        month_run_delay_seconds=20,
    )


@pytest.fixture
def run_service(
    run_repo: FakeRunRepository,
    month_repo: FakeMonthRepository,
    task_queue: FakeTaskQueue,
    entitlement_service: EntitlementService,
    settings: Settings,
    clock: FixedClock,
) -> RunService:
    return RunService(
        run_repo=run_repo,
        month_repo=month_repo,
        task_queue=task_queue,
        entitlement_service=entitlement_service,
        settings=settings,
        clock=clock,
    )


async def test_ac004_4_start_month_run_increments_generation_and_creates_deterministic_task_name(
    run_service: RunService,
    month_repo: FakeMonthRepository,
    run_repo: FakeRunRepository,
    task_queue: FakeTaskQueue,
):
    org_id = "org_test"
    month = "2026-03"

    run1 = await run_service.start_month_run(org_id, month)

    assert run1.generation == 1
    assert run1.run_id == f"month-{org_id}-{month}-1"
    assert run1.kind == RunKind.MONTH
    assert run1.target == month
    assert run1.status == RunStatus.QUEUED

    # Check month record updated
    m1 = await month_repo.get(org_id, month)
    assert m1 is not None
    assert m1.generation == 1
    assert m1.dirty is True

    # Check task queue enqueued with 20s debounce delay
    assert len(task_queue.enqueued_month_tasks) == 1
    enqueued_org, enqueued_month, enqueued_gen, enqueued_delay = task_queue.enqueued_month_tasks[0]
    assert enqueued_org == org_id
    assert enqueued_month == month
    assert enqueued_gen == 1
    assert enqueued_delay == 20

    # Second bump increments generation
    run2 = await run_service.start_month_run(org_id, month)
    assert run2.generation == 2
    assert run2.run_id == f"month-{org_id}-{month}-2"


async def test_ac004_10_runs_disabled_raises_runs_disabled_error(
    run_service: RunService,
    settings: Settings,
):
    settings.runs_enabled = False
    org_id = "org_test"

    with pytest.raises(RunsDisabledError) as exc_info:
        await run_service.start_month_run(org_id, "2026-03")

    assert exc_info.value.status == 503
    assert exc_info.value.code == "RUNS_DISABLED"

    with pytest.raises(RunsDisabledError) as exc_info_doc:
        await run_service.start_document_run(org_id, "doc_123")

    assert exc_info_doc.value.status == 503
    assert exc_info_doc.value.code == "RUNS_DISABLED"


async def test_ac004_11_user_requested_month_run_quota_exceeded(
    run_service: RunService,
    usage_repo: FakeUsageRepository,
):
    org_id = "org_test"
    # Seed usage at maximum allowed (free trial has monthRunsPerDay=60)
    usage_repo.subscriptions[org_id] = Subscription(
        plan_id="free_trial",
        status="ACTIVE",
    )
    usage_repo.days[(org_id, "2026-03-15")] = UsageDay(day="2026-03-15", month_runs=60)

    with pytest.raises(RunQuotaExceededError) as exc_info:
        await run_service.start_month_run(org_id, "2026-03", is_user_request=True)

    assert exc_info.value.status == 429
    assert exc_info.value.code == "RUN_QUOTA_EXCEEDED"


async def test_ac004_11_automatic_month_run_past_quota_delays_and_pauses(
    run_service: RunService,
    usage_repo: FakeUsageRepository,
    month_repo: FakeMonthRepository,
    task_queue: FakeTaskQueue,
):
    org_id = "org_test"
    usage_repo.subscriptions[org_id] = Subscription(
        plan_id="free_trial",
        status="ACTIVE",
    )
    usage_repo.days[(org_id, "2026-03-15")] = UsageDay(day="2026-03-15", month_runs=60)

    # Automatic run is NOT rejected
    run = await run_service.start_month_run(org_id, "2026-03", is_user_request=False)

    assert run.generation == 1
    m = await month_repo.get(org_id, "2026-03")
    assert m is not None
    assert "paused until tomorrow" in (m.note or "").lower()

    # Delay should be scheduled for next day (until midnight)
    _, _, _, delay = task_queue.enqueued_month_tasks[0]
    assert delay > 20


async def test_ac004_1_start_document_run_creates_run_and_enqueues_task(
    run_service: RunService,
    run_repo: FakeRunRepository,
    task_queue: FakeTaskQueue,
):
    org_id = "org_test"
    doc_id = "doc_abc"

    run = await run_service.start_document_run(org_id, doc_id, attempt=1)

    assert run.run_id == f"doc-{doc_id}-1"
    assert run.kind == RunKind.DOCUMENT
    assert run.target == doc_id
    assert run.status == RunStatus.QUEUED

    saved = await run_repo.get(org_id, f"doc-{doc_id}-1")
    assert saved is not None
    assert len(task_queue.enqueued_document_tasks) == 1
    assert task_queue.enqueued_document_tasks[0] == (org_id, doc_id, f"doc-{doc_id}-1", 1)


async def test_ac004_4_month_service_mark_dirty(
    run_service: RunService,
    month_repo: FakeMonthRepository,
    task_queue: FakeTaskQueue,
):
    from app.services.month_service import MonthService

    service = MonthService(month_repo=month_repo, run_service=run_service)
    run_ids = await service.mark_dirty("org_test", ["2026-03", "2026-04"])

    assert len(run_ids) == 2
    assert run_ids[0] == "month-org_test-2026-03-1"
    assert run_ids[1] == "month-org_test-2026-04-1"
    assert len(task_queue.enqueued_month_tasks) == 2
