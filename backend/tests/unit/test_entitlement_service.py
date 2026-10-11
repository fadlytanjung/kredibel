"""EntitlementService: checks and counters in one transaction (T013-07, AC-013-7, -8, -9, -10)."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.adapters.policy_files import load_plans
from app.core.errors import (
    DocumentTooLargeError,
    PlanLimitReachedError,
    RunQuotaExceededError,
    TrialExpiredError,
)
from app.domain.models.workspace import Subscription, UsageMonth
from app.domain.plans import UploadRequest
from app.ports.workspace_repository import UsageSettlement
from app.services.entitlement_service import EntitlementService
from tests.fakes.clock import FixedClock
from tests.fakes.usage_repository import FakeUsageRepository

PLANS = load_plans(Path(__file__).resolve().parents[3] / "contracts" / "plans.v1.yaml")
NOW = datetime(2026, 10, 11, 8, 0, tzinfo=UTC)
ORG = "org_test"
MIB = 1024 * 1024


def _trial(**fields: object) -> Subscription:
    return Subscription.model_validate(
        {
            "plan_id": "free_trial",
            "status": "TRIALING",
            "trial_started_at": NOW - timedelta(days=7),
            "trial_ends_at": NOW + timedelta(days=23),
            **fields,
        }
    )


def _service(
    usage: UsageMonth | None = None, subscription: Subscription | None = None
) -> tuple[EntitlementService, FakeUsageRepository, FixedClock]:
    repo = FakeUsageRepository({ORG: subscription or _trial()})
    if usage is not None:
        repo.months[(ORG, usage.month)] = usage
    clock = FixedClock(NOW)
    return (
        EntitlementService(repo=repo, plans=PLANS, clock=clock, run_quota_per_org_per_day=80),
        repo,
        clock,
    )


def _pdf(pages: int = 3, to_read: int | None = None) -> UploadRequest:
    return UploadRequest(
        size_bytes=MIB, pages=pages, pages_to_read=pages if to_read is None else to_read
    )


async def test_ac013_9_an_allowed_upload_moves_its_counters():
    service, repo, _ = _service()

    await service.reserve_upload(ORG, _pdf(pages=6, to_read=4))

    month = repo.months[(ORG, "2026-10")]
    assert (month.documents_uploaded, month.pages_reserved) == (1, 4)


async def test_ac013_7_an_exact_copy_moves_nothing():
    service, repo, _ = _service()

    await service.reserve_upload(
        ORG, UploadRequest(size_bytes=MIB, pages=3, pages_to_read=0, exact_duplicate=True)
    )

    assert (ORG, "2026-10") not in repo.months


async def test_ac013_7_a_denied_upload_raises_with_numbers_and_moves_nothing():
    service, repo, _ = _service(UsageMonth(month="2026-10", documents_uploaded=150))

    with pytest.raises(PlanLimitReachedError) as exc:
        await service.reserve_upload(ORG, _pdf())

    assert exc.value.extras == {"limit": "documentsPerMonth", "used": 150, "max": 150}
    assert repo.months[(ORG, "2026-10")].documents_uploaded == 150


async def test_ac013_7_size_keeps_its_own_status():
    service, _, _ = _service()

    with pytest.raises(DocumentTooLargeError) as exc:
        await service.reserve_upload(
            ORG, UploadRequest(size_bytes=21 * MIB, pages=1, pages_to_read=1)
        )

    assert exc.value.status == 413


async def test_ac013_8_after_the_trial_uploads_are_refused_with_the_end_date():
    ended = _trial(trial_ends_at=NOW - timedelta(hours=1))
    service, _, _ = _service(subscription=ended)

    with pytest.raises(TrialExpiredError) as exc:
        await service.reserve_upload(ORG, _pdf())

    assert exc.value.extras["trialEndsAt"] == (NOW - timedelta(hours=1)).isoformat()


async def test_ac013_4_overrides_raise_the_demo_workspace_limits():
    demo = _trial(limit_overrides={"documentsPerMonth": 600})
    service, repo, _ = _service(UsageMonth(month="2026-10", documents_uploaded=150), demo)

    await service.reserve_upload(ORG, _pdf())

    assert repo.months[(ORG, "2026-10")].documents_uploaded == 151


async def test_ac013_9_two_uploads_at_the_limit_cannot_both_pass():
    service, repo, _ = _service(UsageMonth(month="2026-10", documents_uploaded=149))

    results = await asyncio.gather(
        service.reserve_upload(ORG, _pdf()),
        service.reserve_upload(ORG, _pdf()),
        return_exceptions=True,
    )

    assert sum(isinstance(r, PlanLimitReachedError) for r in results) == 1
    assert repo.months[(ORG, "2026-10")].documents_uploaded == 150


async def test_ac013_7_usage_months_are_utc():
    service, repo, clock = _service()
    clock.at = datetime(2026, 10, 31, 23, 30, tzinfo=UTC)  # 06:30 on 1 Nov in Jakarta

    await service.reserve_upload(ORG, _pdf())

    assert (ORG, "2026-10") in repo.months


async def test_ac004_11_a_month_run_counts_and_the_quota_says_when_to_retry():
    service, repo, _ = _service()
    repo.days[(ORG, "2026-10-11")] = repo.days_factory("2026-10-11", month_runs=60)

    with pytest.raises(RunQuotaExceededError) as exc:
        await service.reserve_month_run(ORG)

    assert exc.value.status == 429
    assert exc.value.extras["retryAfterSeconds"] == 16 * 3600  # 08:00 UTC to midnight


async def test_ac004_11_an_allowed_month_run_is_counted():
    service, repo, _ = _service()

    await service.reserve_month_run(ORG)

    assert repo.days[(ORG, "2026-10-11")].month_runs == 1


async def test_ac013_10_settlement_replaces_the_reservation_with_actual_use():
    service, repo, _ = _service(UsageMonth(month="2026-10", documents_uploaded=1, pages_reserved=6))

    await service.settle_document_run(
        ORG,
        UsageSettlement(
            month="2026-10",
            pages_reserved=6,
            pages_read=4,
            pages_cached=2,
            ocr_pages=1,
            parser_pages=0,
            ai_spend_usd=Decimal("0.0123"),
        ),
    )

    month = repo.months[(ORG, "2026-10")]
    assert (month.pages_reserved, month.pages_read, month.pages_cached, month.ocr_pages) == (
        4,
        4,
        2,
        1,
    )
    assert month.ai_spend_usd == Decimal("0.0123")
