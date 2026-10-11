"""Pure entitlement checks (T013-03, AC-013-7, AC-013-8)."""

from decimal import Decimal
from pathlib import Path

import pytest

from app.adapters.policy_files import load_plans
from app.domain.models.workspace import UsageDay, UsageMonth
from app.domain.plans import (
    Allowed,
    Denied,
    UploadRequest,
    check_assistant_question,
    check_invite,
    check_month_run,
    check_upload,
    effective_limits,
)

LIMITS = effective_limits(
    load_plans(Path(__file__).resolve().parents[3] / "contracts" / "plans.v1.yaml").plan(
        "free_trial"
    ),
    None,
)
MIB = 1024 * 1024


def _usage(**fields: object) -> UsageMonth:
    return UsageMonth.model_validate({"month": "2026-10", **fields})


def _pdf(pages: int = 3, to_read: int | None = None, size: int = MIB) -> UploadRequest:
    return UploadRequest(
        size_bytes=size, pages=pages, pages_to_read=pages if to_read is None else to_read
    )


def test_ac013_7_an_upload_within_every_limit_is_allowed():
    assert isinstance(check_upload(LIMITS, "TRIALING", _usage(), _pdf()), Allowed)


def test_ac013_8_no_upload_after_the_trial():
    decision = check_upload(LIMITS, "TRIAL_EXPIRED", _usage(), _pdf())

    assert isinstance(decision, Denied)
    assert decision.code == "TRIAL_EXPIRED"


def test_ac013_7_exact_duplicates_never_count():
    full = _usage(documents_uploaded=150, pages_reserved=400)
    copy = UploadRequest(size_bytes=MIB, pages=3, pages_to_read=3, exact_duplicate=True)

    assert isinstance(check_upload(LIMITS, "TRIALING", full, copy), Allowed)


@pytest.mark.parametrize(
    ("request_", "code", "limit", "used", "maximum"),
    [
        (_pdf(size=21 * MIB), "DOCUMENT_TOO_LARGE", "fileSizeMb", 21, 20),
        (_pdf(pages=21), "TOO_MANY_PAGES", "pagesPerDocument", 21, 20),
        (
            UploadRequest(size_bytes=MIB, pages=0, pages_to_read=0, ledger_rows=5001),
            "TOO_MANY_ROWS",
            "ledgerRowsPerFile",
            5001,
            5000,
        ),
    ],
)
def test_ac013_7_size_and_shape_limits(request_, code, limit, used, maximum):
    decision = check_upload(LIMITS, "TRIALING", _usage(), request_)

    assert isinstance(decision, Denied)
    assert (decision.code, decision.limit, decision.used, decision.max) == (
        code,
        limit,
        used,
        maximum,
    )


def test_ac013_7_documents_per_month():
    decision = check_upload(LIMITS, "TRIALING", _usage(documents_uploaded=150), _pdf())

    assert isinstance(decision, Denied)
    assert (decision.code, decision.limit, decision.used, decision.max) == (
        "PLAN_LIMIT_REACHED",
        "documentsPerMonth",
        150,
        150,
    )


def test_ac013_7_pages_are_reserved_against_the_monthly_pages():
    decision = check_upload(LIMITS, "TRIALING", _usage(pages_reserved=396), _pdf(pages=6))

    assert isinstance(decision, Denied)
    assert (decision.limit, decision.used, decision.max) == ("extractedPagesPerMonth", 396, 400)


def test_ac013_7_a_fully_cached_document_reserves_no_pages():
    at_limit = _usage(pages_reserved=400)

    assert isinstance(check_upload(LIMITS, "TRIALING", at_limit, _pdf(pages=6, to_read=0)), Allowed)


def test_ac013_7_ai_spend_blocks_new_reading_once_reached():
    spent = _usage(ai_spend_usd=Decimal("5.00"))

    decision = check_upload(LIMITS, "TRIALING", spent, _pdf())

    assert isinstance(decision, Denied)
    assert (decision.limit, decision.used, decision.max) == (
        "aiSpendUsdPerMonth",
        Decimal("5.00"),
        Decimal("5.00"),
    )
    assert isinstance(check_upload(LIMITS, "TRIALING", spent, _pdf(to_read=0)), Allowed)


def test_ac004_11_month_runs_per_day_is_a_run_quota_with_retry_after():
    decision = check_month_run(
        LIMITS,
        "TRIALING",
        UsageDay(day="2026-10-11", month_runs=60),
        global_quota=80,
        seconds_until_reset=3600,
    )

    assert isinstance(decision, Denied)
    assert (decision.code, decision.limit, decision.used, decision.max) == (
        "RUN_QUOTA_EXCEEDED",
        "monthRunsPerDay",
        60,
        60,
    )
    assert decision.retry_after_seconds == 3600


def test_ac004_11_the_global_quota_caps_a_generous_plan():
    generous = LIMITS.model_copy(update={"month_runs_per_day": 200})

    decision = check_month_run(
        generous,
        "TRIALING",
        UsageDay(day="2026-10-11", month_runs=80),
        global_quota=80,
        seconds_until_reset=60,
    )

    assert isinstance(decision, Denied)
    assert decision.max == 80


def test_ac013_8_no_user_month_run_after_the_trial():
    decision = check_month_run(
        LIMITS, "TRIAL_EXPIRED", UsageDay(day="2026-10-11"), global_quota=80, seconds_until_reset=1
    )

    assert isinstance(decision, Denied)
    assert decision.code == "TRIAL_EXPIRED"


def test_ac013_7_assistant_questions_per_day():
    assert isinstance(
        check_assistant_question(LIMITS, "TRIALING", UsageDay(day="2026-10-11")), Allowed
    )
    decision = check_assistant_question(
        LIMITS, "TRIALING", UsageDay(day="2026-10-11", assistant_questions=50)
    )
    assert isinstance(decision, Denied)
    assert (decision.limit, decision.used, decision.max) == ("assistantQuestionsPerDay", 50, 50)


def test_ac013_7_invites_count_against_seats():
    assert isinstance(check_invite(LIMITS, "TRIALING", seats_used=2), Allowed)
    decision = check_invite(LIMITS, "TRIALING", seats_used=3)
    assert isinstance(decision, Denied)
    assert (decision.code, decision.limit, decision.used, decision.max) == (
        "PLAN_LIMIT_REACHED",
        "seats",
        3,
        3,
    )
    expired = check_invite(LIMITS, "TRIAL_EXPIRED", seats_used=0)
    assert isinstance(expired, Denied) and expired.code == "TRIAL_EXPIRED"
