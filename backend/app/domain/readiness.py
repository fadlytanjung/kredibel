"""Loan readiness (spec 025, ADR-028). Pure: the reconciled months in, the report out.

Whether a workspace's books are ready to show a lender, from six checks with thresholds from
contracts/policy/readiness.v1.yaml: enough months of statements (HISTORY), every month of every
account covered (COVERAGE), each month reconciled and mostly matched (RECONCILED), no open critical
or high finding (FINDINGS), no decision waiting (REVIEW), and money in at least what went out
(CASH). Any FAIL makes the report NOT_READY, otherwise any WARN makes it ALMOST_READY. It is the
owner's own check of the books, never a credit decision: there is no score.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

Status = Literal["PASS", "WARN", "FAIL"]
Level = Literal["READY", "ALMOST_READY", "NOT_READY"]
CheckId = Literal["HISTORY", "COVERAGE", "RECONCILED", "FINDINGS", "REVIEW", "CASH"]

ZERO = Decimal("0")
CENT = Decimal("0.01")
RATE = Decimal("0.0001")
SEVERITY_ORDER = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")


@dataclass(frozen=True)
class ReadinessPolicy:
    max_months: int
    fail_below_months: int
    warn_below_months: int
    warn_below_matched_share: Decimal
    fail_severities: frozenset[str]
    warn_severities: frozenset[str]
    warn_above_open_items: int
    warn_on_negative_net: bool
    warn_on_negative_balance_days: bool
    largest_clients: int


def parse_readiness_policy(raw: dict[str, Any]) -> ReadinessPolicy:
    """readiness.v1.yaml; an inconsistent file raises and stops start-up."""
    checks = raw.get("checks") or {}
    history = checks.get("HISTORY") or {}
    reconciled = checks.get("RECONCILED") or {}
    findings = checks.get("FINDINGS") or {}
    review = checks.get("REVIEW") or {}
    cash = checks.get("CASH") or {}
    policy = ReadinessPolicy(
        max_months=int((raw.get("period") or {}).get("maxMonths", 12)),
        fail_below_months=int(history["failBelowMonths"]),
        warn_below_months=int(history["warnBelowMonths"]),
        warn_below_matched_share=Decimal(str(reconciled["warnBelowMatchedShare"])),
        fail_severities=frozenset(findings.get("failSeverities") or ()),
        warn_severities=frozenset(findings.get("warnSeverities") or ()),
        warn_above_open_items=int(review.get("warnAboveOpenItems", 0)),
        warn_on_negative_net=bool(cash.get("warnOnNegativeNet", True)),
        warn_on_negative_balance_days=bool(cash.get("warnOnNegativeBalanceDays", True)),
        largest_clients=int(raw.get("largestClients", 3)),
    )
    if not 0 < policy.fail_below_months <= policy.warn_below_months <= policy.max_months:
        raise ValueError("readiness.v1: 0 < failBelowMonths <= warnBelowMonths <= maxMonths")
    if not ZERO <= policy.warn_below_matched_share <= 1:
        raise ValueError("readiness.v1: warnBelowMatchedShare must be between 0 and 1")
    unknown = (policy.fail_severities | policy.warn_severities) - set(SEVERITY_ORDER)
    if unknown or policy.fail_severities & policy.warn_severities:
        raise ValueError("readiness.v1: failSeverities and warnSeverities are distinct severities")
    if policy.warn_above_open_items < 0 or policy.largest_clients < 0:
        raise ValueError("readiness.v1: warnAboveOpenItems and largestClients are not negative")
    return policy


@dataclass(frozen=True)
class MonthFacts:
    """One month with data, from its month run (figures, risk) and the statements read."""

    month: str  # yyyy-mm
    statements_present: int
    statements_expected: int
    reconciled: bool  # reconciled or waiting for review, and not changed since its last run
    auto_matched: int
    in_scope: int  # bank lines less those excluded from cash
    money_in: Decimal
    money_out: Decimal  # positive
    closing: Decimal | None
    negative_days: int
    risk_level: str | None
    explanation: str | None  # the month run's risk explanation, only when the guard verified it

    @property
    def matched_share(self) -> Decimal | None:
        if self.in_scope <= 0:
            return None
        return (Decimal(self.auto_matched) / Decimal(self.in_scope)).quantize(RATE)

    @property
    def net(self) -> Decimal:
        return self.money_in - self.money_out


@dataclass(frozen=True)
class GapFact:
    """A cash-flow gap (domain/cash_flow.py): MISSING_MONTH, BALANCE_BREAK, ..."""

    kind: str
    month: str | None
    account: str | None


@dataclass(frozen=True)
class OpenFinding:
    finding_id: str
    code: str
    severity: str
    title: str
    month: str | None
    next_step: str | None


@dataclass(frozen=True)
class ReadinessInput:
    months: tuple[MonthFacts, ...]
    gaps: tuple[GapFact, ...] = ()
    findings: tuple[OpenFinding, ...] = ()
    open_review_items: int = 0
    money_in_by_client: tuple[tuple[str, Decimal], ...] = ()
    documents: tuple[tuple[str, int], ...] = ()  # read documents per type


@dataclass(frozen=True)
class Check:
    id: CheckId
    status: Status
    months: tuple[str, ...] = ()
    findings: tuple[OpenFinding, ...] = ()
    count: int | None = None  # the number the words quote: months, items, days
    threshold: str | None = None  # the policy value the words quote


@dataclass(frozen=True)
class Totals:
    months: int
    money_in: Decimal
    money_out: Decimal
    net: Decimal
    average_in: Decimal | None
    average_out: Decimal | None
    average_net: Decimal | None
    matched_share: Decimal | None
    closing: Decimal | None  # the last month's closing balance


@dataclass(frozen=True)
class ClientShare:
    name: str
    money_in: Decimal
    share: Decimal  # of the period's money in


@dataclass(frozen=True)
class Readiness:
    level: Level
    checks: tuple[Check, ...]
    totals: Totals
    months: tuple[MonthFacts, ...]
    clients: tuple[ClientShare, ...]
    documents: tuple[tuple[str, int], ...]


def _months(values: Iterable[str | None]) -> tuple[str, ...]:
    return tuple(sorted({m for m in values if m}))


def _history(months: tuple[MonthFacts, ...], policy: ReadinessPolicy) -> Check:
    covered = sum(1 for m in months if m.statements_present > 0)
    if covered < policy.fail_below_months:
        return Check("HISTORY", "FAIL", count=covered, threshold=str(policy.fail_below_months))
    if covered < policy.warn_below_months:
        return Check("HISTORY", "WARN", count=covered, threshold=str(policy.warn_below_months))
    return Check("HISTORY", "PASS", count=covered)


def _coverage(months: tuple[MonthFacts, ...], gaps: tuple[GapFact, ...], period: set[str]) -> Check:
    missing = _months(
        [m.month for m in months if m.statements_present < m.statements_expected]
        + [g.month for g in gaps if g.kind == "MISSING_MONTH" and g.month in period]
    )
    if missing:
        return Check("COVERAGE", "FAIL", months=missing, count=len(missing))
    breaks = [g for g in gaps if g.kind == "BALANCE_BREAK"]
    if breaks:
        return Check("COVERAGE", "WARN", months=_months(g.month for g in breaks), count=len(breaks))
    return Check("COVERAGE", "PASS")


def _reconciled(months: tuple[MonthFacts, ...], policy: ReadinessPolicy) -> Check:
    threshold = policy.warn_below_matched_share
    short = _months(
        m.month
        for m in months
        if not m.reconciled or (m.matched_share is not None and m.matched_share < threshold)
    )
    status: Status = "WARN" if short else "PASS"
    return Check("RECONCILED", status, months=short, count=len(short), threshold=str(threshold))


def _findings(
    findings: tuple[OpenFinding, ...], period: set[str], policy: ReadinessPolicy
) -> Check:
    def rank(f: OpenFinding) -> tuple[int, str, str]:
        order = SEVERITY_ORDER.index(f.severity) if f.severity in SEVERITY_ORDER else 99
        return order, f.month or "", f.finding_id

    in_period = [f for f in findings if f.month is None or f.month in period]
    failing = [f for f in in_period if f.severity in policy.fail_severities]
    warning = [f for f in in_period if f.severity in policy.warn_severities]
    shown = tuple(sorted(failing + warning, key=rank))
    status: Status = "FAIL" if failing else "WARN" if warning else "PASS"
    return Check(
        "FINDINGS",
        status,
        months=_months(f.month for f in shown),
        findings=shown,
        count=len(shown),
    )


def _review(open_items: int, policy: ReadinessPolicy) -> Check:
    status: Status = "WARN" if open_items > policy.warn_above_open_items else "PASS"
    return Check("REVIEW", status, count=open_items)


def _cash(months: tuple[MonthFacts, ...], policy: ReadinessPolicy) -> Check:
    net = sum((m.net for m in months), ZERO)
    below_zero = [m for m in months if m.negative_days > 0]
    days = sum(m.negative_days for m in below_zero)
    warn = (policy.warn_on_negative_net and net < 0) or (
        policy.warn_on_negative_balance_days and days > 0
    )
    return Check(
        "CASH",
        "WARN" if warn else "PASS",
        months=_months(m.month for m in below_zero),
        count=days,
    )


def _totals(months: tuple[MonthFacts, ...]) -> Totals:
    n = len(months)
    money_in = sum((m.money_in for m in months), ZERO)
    money_out = sum((m.money_out for m in months), ZERO)
    matched = sum(m.auto_matched for m in months)
    in_scope = sum(m.in_scope for m in months)
    closings = [m.closing for m in months if m.closing is not None]

    def average(total: Decimal) -> Decimal | None:
        return (total / n).quantize(CENT) if n else None

    return Totals(
        months=n,
        money_in=money_in,
        money_out=money_out,
        net=money_in - money_out,
        average_in=average(money_in),
        average_out=average(money_out),
        average_net=average(money_in - money_out),
        matched_share=(Decimal(matched) / Decimal(in_scope)).quantize(RATE) if in_scope else None,
        closing=closings[-1] if closings else None,
    )


def _clients(
    by_client: tuple[tuple[str, Decimal], ...], money_in: Decimal, policy: ReadinessPolicy
) -> tuple[ClientShare, ...]:
    if money_in <= 0:
        return ()
    largest = sorted(by_client, key=lambda c: (-c[1], c[0]))[: policy.largest_clients]
    return tuple(
        ClientShare(name, amount, (amount / money_in).quantize(RATE)) for name, amount in largest
    )


def assess_readiness(data: ReadinessInput, policy: ReadinessPolicy) -> Readiness:
    months = tuple(sorted(data.months, key=lambda m: m.month))
    period = {m.month for m in months}
    checks = (
        _history(months, policy),
        _coverage(months, data.gaps, period),
        _reconciled(months, policy),
        _findings(data.findings, period, policy),
        _review(data.open_review_items, policy),
        _cash(months, policy),
    )
    statuses = {c.status for c in checks}
    level: Level = (
        "NOT_READY" if "FAIL" in statuses else "ALMOST_READY" if "WARN" in statuses else "READY"
    )
    totals = _totals(months)
    return Readiness(
        level=level,
        checks=checks,
        totals=totals,
        months=months,
        clients=_clients(data.money_in_by_client, totals.money_in, policy),
        documents=tuple(sorted(data.documents)),
    )
