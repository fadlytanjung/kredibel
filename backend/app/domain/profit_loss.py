"""Company management P&L from posted GL activity (spec 018, ADR-027), or, while a workspace has
no ledger export, a cash-basis report from its categorized bank lines by subledger label (ADR-027
amendment of 16 Oct 2026). Pure."""

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

from app.domain.categorize import CategoryPolicy
from app.domain.models.bank_line import BankLine
from app.domain.period import resolve_period

ZERO = Decimal("0")


class ReportModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class LedgerRow(ReportModel):
    entry_id: str
    doc_id: str
    row_number: int = Field(ge=1)
    date: date
    account_code: str
    account_name: str
    debit: Decimal = Field(ge=0, allow_inf_nan=False)
    credit: Decimal = Field(ge=0, allow_inf_nan=False)
    currency: str | None = None
    posting_status: Literal["POSTED", "DRAFT", "UNKNOWN"] = "UNKNOWN"
    journal_id: str | None = None
    # The row's own words (docs/08 §6.2): what a bank line's booking is matched by.
    description: str = ""
    reference: str | None = None
    entry_kind: Literal["ACTIVITY", "OPENING", "CLOSING"] = "ACTIVITY"
    held_as_duplicate: bool = False
    # D06: {code, ofEntryId, decision} once the row repeats an earlier entry (docs/09 §3.8)
    duplicate: dict[str, Any] | None = None

    @field_validator("debit", "credit", mode="before")
    @classmethod
    def no_float(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("Money must be a decimal string or Decimal")
        return value

    @model_validator(mode="after")
    def one_side(self) -> "LedgerRow":
        if self.debit and self.credit:
            raise ValueError("A ledger row cannot have both a debit and a credit")
        return self


class Classification(ReportModel):
    account_code: str = Field(min_length=1, max_length=100)
    pnl_line: str
    subledger: str


class PnlPolicyLine(BaseModel):
    label: str
    normal_balance: Literal["DEBIT", "CREDIT", "NONE"] = Field(alias="normalBalance")


class ProfitLossPolicy(BaseModel):
    version: Literal[1]
    basis: Literal["ACCRUAL"]
    lines: dict[str, PnlPolicyLine]
    subledgers: dict[str, str]

    @model_validator(mode="after")
    def required_lines(self) -> "ProfitLossPolicy":
        expected = {
            "REVENUE": "CREDIT",
            "OTHER_INCOME": "CREDIT",
            "COST_OF_SALES": "DEBIT",
            "OPERATING_EXPENSES": "DEBIT",
            "FINANCE_COSTS": "DEBIT",
            "INCOME_TAX": "DEBIT",
            "BALANCE_SHEET": "NONE",
        }
        if {key: value.normal_balance for key, value in self.lines.items()} != expected:
            raise ValueError("Invalid P&L policy lines or normal balances")
        if not self.subledgers:
            raise ValueError("Subledger families are required")
        return self


class ProfitLine(ReportModel):
    id: str
    amount: Decimal | None
    fact_id: str
    entry_ids: list[str]


class ProfitEntry(ReportModel):
    entry_id: str
    doc_id: str
    row_number: int
    date: date
    account_code: str
    account_name: str
    pnl_line: str
    subledger: str
    amount: Decimal


class ProfitLoss(ReportModel):
    period: str
    months: list[str]
    currency: str
    basis: Literal["ACCRUAL", "CASH"] = "ACCRUAL"
    coverage: Literal["IMPORTED_ENTRIES_ONLY", "BANK_LINES_ONLY"] = "IMPORTED_ENTRIES_ONLY"
    status: Literal["UNAVAILABLE", "PARTIAL", "IMPORTED"]
    lines: list[ProfitLine]
    entries: list[ProfitEntry]
    exclusions: dict[str, int]
    gaps: list[str]
    classified_count: int
    input_count: int


def build_profit_loss(
    rows: list[LedgerRow],
    classifications: dict[str, Classification],
    policy: ProfitLossPolicy,
    *,
    currency: str,
    period: str,
    excluded_docs: dict[str, str] | None = None,
) -> ProfitLoss:
    resolved = resolve_period(period, [r.date.strftime("%Y-%m") for r in rows])
    scoped = sorted(
        [r for r in rows if r.date.strftime("%Y-%m") in resolved.months],
        key=lambda r: (r.date, r.entry_id, r.doc_id, r.row_number),
    )
    occurrences = Counter(r.entry_id for r in scoped)
    excluded: Counter[str] = Counter()
    gaps: set[str] = set()
    entries: list[ProfitEntry] = []
    journals: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    eligible = classified = 0
    for row in scoped:
        reason = (excluded_docs or {}).get(row.doc_id)
        if not reason:
            reason = _exclusion(row, occurrences)
        if not reason and row.currency != currency:
            reason = "CURRENCY"
        if reason:
            excluded[reason] += 1
            continue
        eligible += 1
        if not row.journal_id:
            gaps.add("MISSING_JOURNAL_ID")
        journals[(row.doc_id, row.journal_id or "")] += row.debit - row.credit
        mapping = classifications.get(row.account_code)
        if (
            mapping is None
            or mapping.pnl_line not in policy.lines
            or mapping.subledger not in policy.subledgers
        ):
            excluded["UNCLASSIFIED"] += 1
            continue
        classified += 1
        line = policy.lines[mapping.pnl_line]
        if line.normal_balance == "NONE":
            continue
        amount = (
            row.credit - row.debit if line.normal_balance == "CREDIT" else row.debit - row.credit
        )
        entries.append(
            ProfitEntry(
                entry_id=row.entry_id,
                doc_id=row.doc_id,
                row_number=row.row_number,
                date=row.date,
                account_code=row.account_code,
                account_name=row.account_name,
                pnl_line=mapping.pnl_line,
                subledger=mapping.subledger,
                amount=amount,
            )
        )
    if any(value != ZERO for value in journals.values()):
        gaps.add("UNBALANCED_JOURNAL")
    status = "UNAVAILABLE" if not eligible else ("PARTIAL" if excluded or gaps else "IMPORTED")
    # A balanced import containing only classified balance-sheet activity can have zero P&L.
    available = classified > 0 and (bool(entries) or classified == eligible)
    return ProfitLoss(
        period=resolved.key,
        months=list(resolved.months),
        currency=currency,
        status=status,
        lines=_lines(entries, resolved.key, available),
        entries=entries,
        exclusions=dict(sorted(excluded.items())),
        gaps=sorted(gaps),
        classified_count=classified,
        input_count=len(scoped),
    )


def build_cash_profit_loss(
    lines: list[BankLine],
    categories: CategoryPolicy,
    policy: ProfitLossPolicy,
    *,
    currency: str,
    period: str,
    excluded_docs: dict[str, str] | None = None,
) -> ProfitLoss:
    """A cash-basis profit and loss from categorized bank lines, for a workspace without a ledger
    export: each category's policy gives the P&L line and the subledger label; money in on a credit
    line is revenue, money out on a debit line is an expense, a refund reverses its own line.
    Transfers and reversals are not cash flows of the business; uncategorized lines make the report
    partial; balance-sheet categories (equipment, loans, owner) never become profit or expense."""
    resolved = resolve_period(period, [line.month for line in lines])
    scoped = sorted(
        [line for line in lines if line.month in resolved.months],
        key=lambda line: (line.date, line.doc_id, line.row_index, line.tx_id),
    )
    excluded: Counter[str] = Counter()
    entries: list[ProfitEntry] = []
    eligible = classified = 0
    for line in scoped:
        reason = (excluded_docs or {}).get(line.doc_id)
        if reason:
            excluded[reason] += 1
            continue
        category = categories.categories.get(line.category)
        if category is None or line.category == "UNKNOWN":
            eligible += 1
            excluded["UNCATEGORIZED"] += 1
            continue
        if category.pnl_line is None or category.subledger is None:
            excluded["NOT_CASH_FLOW"] += 1
            continue
        eligible += 1
        pnl_line = policy.lines.get(category.pnl_line)
        if pnl_line is None or category.subledger not in policy.subledgers:
            excluded["UNCLASSIFIED"] += 1
            continue
        classified += 1
        if pnl_line.normal_balance == "NONE":
            continue
        amount = line.amount if pnl_line.normal_balance == "CREDIT" else -line.amount
        entries.append(
            ProfitEntry(
                entry_id=line.tx_id,
                doc_id=line.doc_id,
                row_number=line.row_index + 1,
                date=line.date,
                account_code=category.id,
                account_name=category.label,
                pnl_line=category.pnl_line,
                subledger=category.subledger,
                amount=amount,
            )
        )
    status = "UNAVAILABLE" if not eligible else ("PARTIAL" if excluded else "IMPORTED")
    available = classified > 0 and (bool(entries) or classified == eligible)
    return ProfitLoss(
        period=resolved.key,
        months=list(resolved.months),
        currency=currency,
        basis="CASH",
        coverage="BANK_LINES_ONLY",
        status=status,
        lines=_lines(entries, resolved.key, available),
        entries=entries,
        exclusions=dict(sorted(excluded.items())),
        gaps=["NO_LEDGER_EXPORT"],
        classified_count=classified,
        input_count=len(scoped),
    )


def _exclusion(row: LedgerRow, occurrences: Counter[str]) -> str | None:
    if occurrences[row.entry_id] > 1:
        return "DUPLICATE_ENTRY_ID"
    if row.held_as_duplicate:
        return "HELD_DUPLICATE"
    if row.posting_status != "POSTED":
        return "NOT_POSTED"
    if row.entry_kind != "ACTIVITY":
        return "NON_ACTIVITY"
    return None


def _lines(entries: list[ProfitEntry], period: str, available: bool) -> list[ProfitLine]:
    parts = {
        "REVENUE": {"REVENUE": 1},
        "COST_OF_SALES": {"COST_OF_SALES": 1},
        "GROSS_PROFIT": {"REVENUE": 1, "COST_OF_SALES": -1},
        "OPERATING_EXPENSES": {"OPERATING_EXPENSES": 1},
        "OPERATING_PROFIT": {"REVENUE": 1, "COST_OF_SALES": -1, "OPERATING_EXPENSES": -1},
        "OTHER_INCOME": {"OTHER_INCOME": 1},
        "FINANCE_COSTS": {"FINANCE_COSTS": 1},
        "INCOME_TAX": {"INCOME_TAX": 1},
        "NET_PROFIT": {
            "REVENUE": 1,
            "COST_OF_SALES": -1,
            "OPERATING_EXPENSES": -1,
            "OTHER_INCOME": 1,
            "FINANCE_COSTS": -1,
            "INCOME_TAX": -1,
        },
    }
    fingerprint = sha256((period + repr([e.model_dump() for e in entries])).encode()).hexdigest()[
        :16
    ]
    return [
        ProfitLine(
            id=key,
            amount=sum((e.amount * sign[e.pnl_line] for e in entries if e.pnl_line in sign), ZERO)
            if available
            else None,
            fact_id=f"fact:pnl_{fingerprint}:{key.lower()}",
            entry_ids=[e.entry_id for e in entries if e.pnl_line in sign],
        )
        for key, sign in parts.items()
    ]
