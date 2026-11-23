"""Loan readiness (spec 025, ADR-028): six checks computed by code from the reconciled months and
the policy, a level from the worst of them, and the figures a lender reads first. Not a credit
decision. Synthetic data only."""

import random
from decimal import Decimal as D
from pathlib import Path

import pytest
import yaml

from app.domain.readiness import (
    GapFact,
    MonthFacts,
    OpenFinding,
    ReadinessInput,
    ReadinessPolicy,
    assess_readiness,
    parse_readiness_policy,
)

POLICY_FILE = Path(__file__).resolve().parents[3] / "contracts" / "policy" / "readiness.v1.yaml"


@pytest.fixture(scope="module")
def policy() -> ReadinessPolicy:
    return parse_readiness_policy(yaml.safe_load(POLICY_FILE.read_text(encoding="utf-8")))


def month(m: str, **changes) -> MonthFacts:
    base = {
        "month": m,
        "statements_present": 1,
        "statements_expected": 1,
        "reconciled": True,
        "auto_matched": 95,
        "in_scope": 100,
        "money_in": D("100000000.00"),
        "money_out": D("80000000.00"),
        "closing": D("50000000.00"),
        "negative_days": 0,
        "risk_level": "LOW",
        "explanation": None,
    }
    return MonthFacts(**{**base, **changes})


SIX = tuple(month(f"2026-{m:02d}") for m in range(5, 11))


def finding(code: str, severity: str, m: str | None, fid: str | None = None) -> OpenFinding:
    return OpenFinding(
        finding_id=fid or f"fnd_{code}_{m}",
        code=code,
        severity=severity,
        title=f"{code} title",
        month=m,
        next_step=f"Next step for {code}",
    )


def check(report, check_id: str):
    return next(c for c in report.checks if c.id == check_id)


def test_ac025_1_clean_books_of_six_months_are_ready(policy):
    report = assess_readiness(ReadinessInput(months=SIX), policy)

    assert report.level == "READY"
    assert [c.id for c in report.checks] == [
        "HISTORY",
        "COVERAGE",
        "RECONCILED",
        "FINDINGS",
        "REVIEW",
        "CASH",
    ]
    assert {c.status for c in report.checks} == {"PASS"}
    assert check(report, "HISTORY").count == 6


@pytest.mark.parametrize(
    ("n", "status", "level"),
    [
        (2, "FAIL", "NOT_READY"),
        (3, "WARN", "ALMOST_READY"),
        (5, "WARN", "ALMOST_READY"),
        (6, "PASS", "READY"),
    ],
)
def test_ac025_1_history_needs_three_months_and_six_to_pass(policy, n, status, level):
    report = assess_readiness(ReadinessInput(months=SIX[:n]), policy)

    history = check(report, "HISTORY")
    assert history.status == status
    assert history.count == n
    assert report.level == level


def test_ac025_3_a_missing_statement_fails_coverage_and_names_the_month(policy):
    months = (*SIX[:3], month("2026-08", statements_present=0, statements_expected=1), *SIX[4:])
    gaps = (GapFact("MISSING_MONTH", "2026-09", "BCA ••••1234"),)

    report = assess_readiness(ReadinessInput(months=months, gaps=gaps), policy)

    coverage = check(report, "COVERAGE")
    assert coverage.status == "FAIL"
    assert coverage.months == ("2026-08", "2026-09")
    assert report.level == "NOT_READY"


def test_ac025_3_balances_that_do_not_carry_over_warn(policy):
    gaps = (
        GapFact("BALANCE_BREAK", None, "BCA ••••1234"),
        GapFact("TRANSFERS_ELSEWHERE", None, None),
    )

    coverage = check(assess_readiness(ReadinessInput(months=SIX, gaps=gaps), policy), "COVERAGE")

    assert coverage.status == "WARN"
    assert coverage.count == 1


def test_ac025_3_months_not_reconciled_or_under_the_matched_share_warn(policy):
    months = (
        *SIX[:4],
        month("2026-09", reconciled=False),
        month("2026-10", auto_matched=80, in_scope=100),
    )

    reconciled = check(assess_readiness(ReadinessInput(months=months), policy), "RECONCILED")

    assert reconciled.status == "WARN"
    assert reconciled.months == ("2026-09", "2026-10")
    assert reconciled.threshold == "0.85"


def test_ac025_3_an_open_critical_finding_fails_and_a_high_one_warns_with_its_evidence(policy):
    findings = (
        finding("X08_SUPPLIER_ACCOUNT_CHANGED", "HIGH", "2026-10"),
        finding("A01_RUNNING_BALANCE_BREAK", "CRITICAL", "2026-08"),
        finding("R01_SALES_INVOICE_OVERDUE", "MEDIUM", "2026-09"),
        finding("A01_RUNNING_BALANCE_BREAK", "CRITICAL", "2025-01", fid="outside"),
    )

    report = assess_readiness(ReadinessInput(months=SIX, findings=findings), policy)

    found = check(report, "FINDINGS")
    assert found.status == "FAIL"
    assert [f.code for f in found.findings] == [
        "A01_RUNNING_BALANCE_BREAK",
        "X08_SUPPLIER_ACCOUNT_CHANGED",
    ]
    assert found.findings[0].next_step == "Next step for A01_RUNNING_BALANCE_BREAK"
    assert found.months == ("2026-08", "2026-10")
    assert report.level == "NOT_READY"

    only_high = assess_readiness(ReadinessInput(months=SIX, findings=findings[:1]), policy)
    assert check(only_high, "FINDINGS").status == "WARN"
    assert only_high.level == "ALMOST_READY"


def test_ac025_3_a_finding_without_a_month_still_counts(policy):
    report = assess_readiness(
        ReadinessInput(
            months=SIX, findings=(finding("M04_FONT_ANOMALY_IN_VALUES", "CRITICAL", None),)
        ),
        policy,
    )

    assert check(report, "FINDINGS").status == "FAIL"


def test_ac025_3_open_review_items_warn_with_their_count(policy):
    review = check(
        assess_readiness(ReadinessInput(months=SIX, open_review_items=4), policy), "REVIEW"
    )

    assert (review.status, review.count) == ("WARN", 4)


def test_ac025_3_negative_net_and_days_below_zero_warn(policy):
    months = (*SIX[:5], month("2026-10", money_out=D("700000000.00"), negative_days=3))

    cash = check(assess_readiness(ReadinessInput(months=months), policy), "CASH")

    assert cash.status == "WARN"
    assert cash.months == ("2026-10",)
    assert cash.count == 3


def test_ac025_2_totals_averages_and_the_overall_matched_share(policy):
    months = (
        month(
            "2026-08",
            money_in=D("100.00"),
            money_out=D("40.00"),
            auto_matched=90,
            in_scope=100,
            closing=D("10.00"),
        ),
        month(
            "2026-09",
            money_in=D("200.00"),
            money_out=D("100.00"),
            auto_matched=50,
            in_scope=50,
            closing=D("70.00"),
        ),
        month(
            "2026-10",
            money_in=D("0.01"),
            money_out=D("0.00"),
            auto_matched=0,
            in_scope=0,
            closing=None,
        ),
    )

    totals = assess_readiness(ReadinessInput(months=months), policy).totals

    assert totals.months == 3
    assert totals.money_in == D("300.01")
    assert totals.money_out == D("140.00")
    assert totals.net == D("160.01")
    assert totals.average_in == D("100.00")
    assert totals.average_out == D("46.67")
    assert totals.average_net == D("53.34")
    assert totals.matched_share == D("0.9333")
    assert totals.closing == D("70.00")


def test_ac025_2_the_largest_clients_and_their_share_of_money_in(policy):
    months = (month("2026-10", money_in=D("1000.00")),)
    clients = (
        ("Kopi Senja", D("100.00")),
        ("Hotel Braga", D("400.00")),
        ("Cafe Dago", D("250.00")),
        ("Warung Ani", D("50.00")),
    )

    report = assess_readiness(ReadinessInput(months=months, money_in_by_client=clients), policy)

    assert [(c.name, c.share) for c in report.clients] == [
        ("Hotel Braga", D("0.4000")),
        ("Cafe Dago", D("0.2500")),
        ("Kopi Senja", D("0.1000")),
    ]


def test_ac025_1_the_same_books_in_any_order_give_the_same_report(policy):
    findings = (
        finding("X08_SUPPLIER_ACCOUNT_CHANGED", "HIGH", "2026-10"),
        finding("A01_RUNNING_BALANCE_BREAK", "CRITICAL", "2026-08"),
    )
    months = list(SIX)
    first = assess_readiness(ReadinessInput(months=tuple(months), findings=findings), policy)
    random.Random(7).shuffle(months)

    again = assess_readiness(ReadinessInput(months=tuple(months), findings=findings[::-1]), policy)

    assert again == first
    assert [m.month for m in again.months] == [m.month for m in SIX]


def test_ac025_5_no_statement_is_not_ready(policy):
    report = assess_readiness(ReadinessInput(months=()), policy)

    assert report.level == "NOT_READY"
    assert check(report, "HISTORY").status == "FAIL"
    assert report.totals.months == 0
    assert report.totals.average_in is None


def test_the_policy_must_be_consistent():
    raw = yaml.safe_load(POLICY_FILE.read_text(encoding="utf-8"))
    raw["checks"]["HISTORY"]["warnBelowMonths"] = 2
    with pytest.raises(ValueError, match="warnBelowMonths"):
        parse_readiness_policy(raw)
    raw = yaml.safe_load(POLICY_FILE.read_text(encoding="utf-8"))
    raw["checks"]["RECONCILED"]["warnBelowMatchedShare"] = "1.5"
    with pytest.raises(ValueError, match="warnBelowMatchedShare"):
        parse_readiness_policy(raw)
