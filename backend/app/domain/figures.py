"""A month's figures as facts (docs/08 §5, ADR-025). Pure: lines, records and allocations in.

Every number has an ID (`fact:2026-03:money_in`) and its inputs, so explanations and the assistant
can cite it. Bank cash comes only from eligible statement rows (the caller leaves out held, failed
and quarantined statements and documents whose currency was not accepted), each counted once whether
or not a document supports it; a person's payment confirmation never adds to it.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from app.domain.categorize import CategoryPolicy
from app.domain.models.bank_line import BankLine
from app.domain.models.invoice import Invoice, Receipt
from app.domain.reconcile import Allocation

ZERO = Decimal("0")
RATE = Decimal("0.0001")


@dataclass(frozen=True)
class Fact:
    fact_id: str
    value: str  # a decimal string or a count
    inputs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"factId": self.fact_id, "value": self.value, "inputs": list(self.inputs)}


@dataclass
class AccountLines:
    """One account's eligible lines dated in the month."""

    account: str  # bank and masked number, e.g. "RHB Bank Berhad ••••3876"
    lines: list[BankLine] = field(default_factory=list)


def _money(v: Decimal) -> str:
    return f"{v:.2f}"


def _balances(lines: list[BankLine]) -> tuple[Decimal | None, Decimal | None, dict[date, Decimal]]:
    """Opening (the balance before the month's first line), closing, and end-of-day balances."""
    ordered = sorted(lines, key=lambda ln: (ln.date, ln.doc_id, ln.row_index))
    printed = [(ln, ln.balance) for ln in ordered if ln.balance is not None]
    if not printed:
        return None, None, {}
    first, first_balance = printed[0]
    end_of_day = {ln.date: balance for ln, balance in printed}
    return first_balance - first.amount, printed[-1][1], end_of_day


def month_figures(
    month: str,
    accounts: Sequence[AccountLines],
    invoices: Sequence[Invoice],
    receipts: Sequence[Receipt],
    categories: CategoryPolicy,
    allocations: Sequence[Allocation],
) -> dict[str, Fact]:
    def fact(name: str, value: Decimal | int, inputs: Sequence[str] = ()) -> Fact:
        text = _money(value) if isinstance(value, Decimal) else str(value)
        return Fact(f"fact:{month}:{name}", text, tuple(inputs))

    lines = [ln for a in accounts for ln in a.lines]
    cash = [ln for ln in lines if ln.cashflow_class != "NON_CASH"]
    credits = [ln for ln in cash if ln.amount > 0]
    debits = [ln for ln in cash if ln.amount < 0]
    money_in = sum((ln.amount for ln in credits), ZERO)
    money_out = -sum((ln.amount for ln in debits), ZERO)
    operating = [ln for ln in cash if ln.cashflow_class == "OPERATING"]
    facts = {
        "money_in": fact("money_in", money_in, [ln.tx_id for ln in credits]),
        "money_out": fact("money_out", money_out, [ln.tx_id for ln in debits]),
        "net": fact(
            "net", money_in - money_out, [f"fact:{month}:money_in", f"fact:{month}:money_out"]
        ),
        "operating_in": fact(
            "operating_in", sum((ln.amount for ln in operating if ln.amount > 0), ZERO)
        ),
        "operating_out": fact(
            "operating_out", -sum((ln.amount for ln in operating if ln.amount < 0), ZERO)
        ),
        "uncategorized": fact("uncategorized", sum(1 for ln in lines if ln.category == "UNKNOWN")),
    }

    opening = closing = ZERO
    have_balances = False
    negative: set[date] = set()
    for account in accounts:
        first, last, days = _balances(account.lines)
        if first is None or last is None:
            continue
        have_balances = True
        opening += first
        closing += last
        negative |= {d for d, b in days.items() if b < 0}
    if have_balances:
        facts["opening"] = fact("opening", opening)
        facts["closing"] = fact("closing", closing)
    facts["negative_days"] = fact("negative_days", len(negative))

    # Support is a separate dimension from cash (ADR-025): an unmatched line is still bank cash.
    state: dict[str, str] = {}
    for a in allocations:
        label = a.method or "PROPOSED"  # AUTO, MANUAL or PROPOSED
        for tx in a.left_ids:
            state[tx] = label
    excluded = [ln for ln in lines if ln.cashflow_class == "NON_CASH"]
    in_scope = [ln for ln in lines if ln.cashflow_class != "NON_CASH"]
    auto = [ln.tx_id for ln in in_scope if state.get(ln.tx_id) == "AUTO"]
    facts["bank_lines"] = fact("bank_lines", len(lines))
    facts["excluded"] = fact("excluded", len(excluded), [ln.tx_id for ln in excluded])
    facts["auto_matched"] = fact("auto_matched", len(auto), auto)
    facts["manually_matched"] = fact(
        "manually_matched", sum(1 for ln in in_scope if state.get(ln.tx_id) == "MANUAL")
    )
    facts["proposed"] = fact(
        "proposed", sum(1 for ln in in_scope if state.get(ln.tx_id) == "PROPOSED")
    )
    facts["unmatched"] = fact("unmatched", sum(1 for ln in in_scope if ln.tx_id not in state))
    rate = Decimal(len(auto)) / len(in_scope) if in_scope else ZERO
    facts["auto_match_rate"] = Fact(
        f"fact:{month}:auto_match_rate",
        str(rate.quantize(RATE)),
        (f"fact:{month}:auto_matched", f"fact:{month}:bank_lines", f"fact:{month}:excluded"),
    )

    by_category: dict[str, Decimal] = defaultdict(lambda: ZERO)
    by_line: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for ln in cash:
        by_category[ln.category] += ln.amount
        by_line[categories.categories[ln.category].line] += ln.amount
    for name, total in sorted(by_category.items()):
        facts[f"category:{name}"] = fact(f"category:{name}", total)
    for name, total in sorted(by_line.items()):
        facts[f"line:{name}"] = fact(f"line:{name}", total)

    sales = [i for i in invoices if i.kind == "SALES" and i.total is not None]
    purchases = [i for i in invoices if i.kind == "PURCHASE" and i.total is not None]
    paid = [r for r in receipts if r.total is not None]
    facts["invoiced_sales"] = fact(
        "invoiced_sales", sum((i.total or ZERO for i in sales), ZERO), [i.invoice_id for i in sales]
    )
    facts["invoiced_purchases"] = fact(
        "invoiced_purchases",
        sum((i.total or ZERO for i in purchases), ZERO),
        [i.invoice_id for i in purchases],
    )
    facts["receipts_total"] = fact(
        "receipts_total", sum((r.total or ZERO for r in paid), ZERO), [r.receipt_id for r in paid]
    )
    return facts
