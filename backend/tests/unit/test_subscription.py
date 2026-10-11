"""Effective limits and trial status (T013-02, AC-013-4, AC-013-8)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.adapters.policy_files import load_plans
from app.domain.models.workspace import Subscription
from app.domain.plans import effective_limits, subscription_status, trial_days_left

CATALOG = load_plans(Path(__file__).resolve().parents[3] / "contracts" / "plans.v1.yaml")
TRIAL = CATALOG.plan("free_trial")
START = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


def _sub(**overrides: object) -> Subscription:
    fields: dict[str, object] = {
        "plan_id": "free_trial",
        "status": "TRIALING",
        "trial_started_at": START,
        "trial_ends_at": START + timedelta(days=30),
    }
    fields.update(overrides)
    return Subscription.model_validate(fields)


def test_ac013_4_limits_are_the_plans_without_overrides():
    limits = effective_limits(TRIAL, None)

    assert limits.documents_per_month == 150
    assert limits.ai_spend_usd_per_month == Decimal("5.00")


def test_ac013_4_overrides_replace_only_the_limits_they_name():
    overrides = {
        "documentsPerMonth": 600,
        "extractedPagesPerMonth": 3000,
        "monthRunsPerDay": 200,
        "aiSpendUsdPerMonth": "40.00",
    }

    limits = effective_limits(TRIAL, overrides)

    assert limits.documents_per_month == 600
    assert limits.extracted_pages_per_month == 3000
    assert limits.month_runs_per_day == 200
    assert limits.ai_spend_usd_per_month == Decimal("40.00")
    assert limits.pages_per_document == 20


def test_ac013_4_an_unknown_override_is_rejected():
    with pytest.raises(ValidationError):
        effective_limits(TRIAL, {"documentsPerYear": 1})


def test_ac013_8_trialing_before_trial_end():
    now = START + timedelta(days=7)

    assert subscription_status(_sub(), now) == "TRIALING"
    assert trial_days_left(_sub(), now) == 23


def test_ac013_8_expired_at_and_after_trial_end():
    sub = _sub()
    ends = START + timedelta(days=30)

    assert subscription_status(sub, ends) == "TRIAL_EXPIRED"
    assert subscription_status(sub, ends + timedelta(days=3)) == "TRIAL_EXPIRED"
    assert trial_days_left(sub, ends + timedelta(days=3)) == 0


def test_ac013_8_a_part_day_counts_as_a_day_left():
    sub = _sub()
    one_hour_before_end = START + timedelta(days=30) - timedelta(hours=1)

    assert trial_days_left(sub, one_hour_before_end) == 1


def test_ac013_8_stored_status_does_not_keep_an_ended_trial_alive():
    """The status is derived from the clock; a stale TRIALING in Firestore does not matter."""
    sub = _sub(status="TRIALING")

    assert subscription_status(sub, START + timedelta(days=45)) == "TRIAL_EXPIRED"
