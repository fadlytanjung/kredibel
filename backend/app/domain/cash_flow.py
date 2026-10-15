"""Money in and out by month, and the cash-flow statement (docs/08 §5.2; spec 010, T010-01b). Pure.

opening + Σ activities = closing is checked per account in code. When it does not hold the result
lists why (a missing month, no printed balances, a balance break, transfers to or from an account
without statements), so the chart never draws a balance that does not exist. Wording from
categories.v1.yaml; transfers between own accounts and reversals are not activities.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from app.domain.categorize import Category, CategoryPolicy, Framework
from app.domain.models.bank_line import BankLine

GapKind = Literal["MISSING_MONTH", "NO_BALANCES", "BALANCE_BREAK", "TRANSFERS_ELSEWHERE"]

ZERO = Decimal("0")
ACTIVITIES = ("OPERATING", "INVESTING", "FINANCING")


@dataclass(frozen=True)
class MonthCash:
    month: str
    money_in: Decimal
    money_out: Decimal
    net: Decimal
    closing: Decimal | None  # Σ of each account's latest balance up to the month's end
    risk_level: str | None = None


@dataclass(frozen=True)
class LineAmount:
    line: str
    category: str | None  # set for lines shown per category (split, or not categorized)
    label: str
    cashflow_class: str
    amount: Decimal  # credits less debits


@dataclass(frozen=True)
class Gap:
    kind: GapKind
    month: str | None = None
    account: str | None = None
    amount: Decimal | None = None


@dataclass(frozen=True)
class CashFlow:
    framework: Framework
    months: tuple[MonthCash, ...]
    opening: Decimal | None
    closing: Decimal | None
    by_activity: dict[str, Decimal]
    by_line: tuple[LineAmount, ...]
    gaps: tuple[Gap, ...] = field(default_factory=tuple)
    note: str | None = None

    @property
    def balanced(self) -> bool:
        return not self.gaps


@dataclass
class _Account:
    name: str
    lines: list[BankLine]

    def anchors(self) -> tuple[Decimal, Decimal] | None:
        """Opening and closing from the printed balances, or None when nothing is printed."""
        printed = [(i, ln.balance) for i, ln in enumerate(self.lines) if ln.balance is not None]
        if not printed:
            return None
        (first, first_balance), (last, last_balance) = printed[0], printed[-1]
        opening = first_balance - sum((ln.amount for ln in self.lines[: first + 1]), ZERO)
        closing = last_balance + sum((ln.amount for ln in self.lines[last + 1 :]), ZERO)
        return opening, closing

    def balance_at_end_of(self, month: str) -> Decimal | None:
        anchors = self.anchors()
        if anchors is None or not any(ln.month <= month for ln in self.lines):
            return None
        return anchors[0] + sum((ln.amount for ln in self.lines if ln.month <= month), ZERO)


def build_cash_flow(
    lines: list[BankLine],
    *,
    months: list[str],
    account_of: dict[str, str],
    policy: CategoryPolicy,
    framework: Framework,
    risk: dict[str, str] | None = None,
    held_docs: frozenset[str] = frozenset(),
) -> CashFlow:
    """`months` are the period's months in order; `account_of` maps a statement's docId to its
    account (bank and masked number); `risk` gives a month's risk level."""
    unknown = policy.categories["UNKNOWN"]
    in_period = set(months)

    def category(line: BankLine) -> Category:
        return policy.categories.get(line.category, unknown)

    counted = sorted(
        (ln for ln in lines if ln.doc_id not in held_docs and ln.month in in_period),
        key=lambda ln: (ln.date, ln.doc_id, ln.row_index),
    )
    accounts: dict[str, _Account] = {}
    for ln in counted:
        name = account_of.get(ln.doc_id) or policy.flow_labels.get("bankAccount", ln.doc_id)
        accounts.setdefault(name, _Account(name, [])).lines.append(ln)

    def is_cash(line: BankLine) -> bool:
        return category(line).cashflow_class(framework) != "NON_CASH"

    series = []
    for month in months:
        of_month = [ln for ln in counted if ln.month == month and is_cash(ln)]
        money_in = sum((ln.amount for ln in of_month if ln.amount > 0), ZERO)
        money_out = -sum((ln.amount for ln in of_month if ln.amount < 0), ZERO)
        ends = [a.balance_at_end_of(month) for a in accounts.values()]
        known = [b for b in ends if b is not None]
        series.append(
            MonthCash(
                month,
                money_in,
                money_out,
                money_in - money_out,
                sum(known, ZERO) if known else None,
                (risk or {}).get(month),
            )
        )

    by_activity: dict[str, Decimal] = {name: ZERO for name in ACTIVITIES}
    # A line keeps its class per framework; one whose categories differ (other income: interest
    # received is investing under IFRS) gets one entry per class.
    by_line: dict[tuple[str, str | None, str], Decimal] = defaultdict(lambda: ZERO)
    transfers = ZERO
    for ln in counted:
        cat = category(ln)
        cls = cat.cashflow_class(framework)
        if cls == "NON_CASH":
            transfers += ln.amount
            continue
        by_activity[cls] = by_activity.get(cls, ZERO) + ln.amount
        per_category = policy.lines[cat.line].split or cls == "UNCLASSIFIED"
        by_line[(cat.line, cat.id if per_category else None, cls)] += ln.amount

    lines_out = [
        LineAmount(
            line_id,
            cat_id,
            policy.categories[cat_id].label
            if cat_id is not None
            else policy.lines[line_id].label(framework),
            cls,
            amount,
        )
        for (line_id, cat_id, cls), amount in sorted(
            by_line.items(),
            key=lambda kv: (policy.lines[kv[0][0]].order, kv[0][1] or "", kv[0][2]),
        )
    ]

    gaps: list[Gap] = []
    openings, closings = [], []
    for account in sorted(accounts.values(), key=lambda a: a.name):
        seen = sorted({ln.month for ln in account.lines})
        gaps += [
            Gap("MISSING_MONTH", month=m, account=account.name)
            for m in months
            if seen[0] < m < seen[-1] and m not in seen
        ]
        anchors = account.anchors()
        if anchors is None:
            gaps.append(Gap("NO_BALANCES", account=account.name))
            continue
        opening, closing = anchors
        openings.append(opening)
        closings.append(closing)
        moved = sum((ln.amount for ln in account.lines), ZERO)
        if opening + moved != closing:
            gaps.append(
                Gap("BALANCE_BREAK", account=account.name, amount=abs(closing - opening - moved))
            )
    if transfers != ZERO:
        gaps.append(Gap("TRANSFERS_ELSEWHERE", amount=transfers))

    moved_by_framework = any(category(ln).ifrs != category(ln).us_gaap for ln in counted)
    return CashFlow(
        framework=framework,
        months=tuple(series),
        opening=sum(openings, ZERO) if openings else None,
        closing=sum(closings, ZERO) if closings else None,
        by_activity=by_activity,
        by_line=tuple(lines_out),
        gaps=tuple(gaps),
        note=policy.framework_notes.get(framework) if moved_by_framework else None,
    )
