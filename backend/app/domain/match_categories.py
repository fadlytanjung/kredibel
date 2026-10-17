"""A category from what a line is matched to (spec 023, AC-023-12). Pure.

The reading categorizes a line from its own words; some lines do not say enough ("CASH DEPOSIT" may
be the day's takings or the owner's money). Once the line is matched for certain, its match can
say: a paid sales invoice is a sales receipt, and a ledger booking is what its other account is
classified as, when that classification names exactly one category for the line's direction. A
line nothing categorized takes it, and so does a line the reading only guessed (below the learning
policy's check threshold, spec 024); a category a person or a rule chose, or the reading was sure
of, stays.
"""

from collections.abc import Mapping, Sequence
from decimal import Decimal

from app.domain.categorize import CategoryPolicy
from app.domain.models.bank_line import BankLine
from app.domain.profit_loss import Classification, LedgerRow, journal_key
from app.domain.reconcile import Allocation


def _from_classification(
    classification: Classification, money_in: bool, policy: CategoryPolicy
) -> str | None:
    direction = "in" if money_in else "out"
    fits = [
        c
        for c in policy.categories.values()
        if c.direction in (direction, "either") and c.pnl_line == classification.pnl_line
    ]
    if len(fits) > 1:
        fits = [c for c in fits if c.subledger == classification.subledger]
    return fits[0].id if len(fits) == 1 else None


def _from_booking(
    entry_id: str,
    money_in: bool,
    rows: Mapping[str, LedgerRow],
    journals: Mapping[tuple[str, ...], Sequence[LedgerRow]],
    classifications: Mapping[str, Classification],
    policy: CategoryPolicy,
) -> str | None:
    row = rows.get(entry_id)
    if row is None:
        return None
    named: set[str | None] = set()
    for other in journals.get(journal_key(row), ()):
        cls = classifications.get(other.account_code)
        if other.entry_id == entry_id or cls is None or cls.pnl_line == "BALANCE_SHEET":
            continue  # the bank account itself, unclassified, or tax and other balances
        named.add(_from_classification(cls, money_in, policy))
    return named.pop() if len(named) == 1 else None


def categories_from_matches(
    lines: Sequence[BankLine],
    allocations: Sequence[Allocation],
    kinds: Mapping[str, str],
    ledger: Sequence[LedgerRow],
    classifications: Mapping[str, Classification],
    policy: CategoryPolicy,
    unsure_below: Decimal | None = None,
) -> dict[str, str]:
    """The category each uncategorized (or only guessed) line's confirmed match names, by ID."""
    rows = {r.entry_id: r for r in ledger}
    journals: dict[tuple[str, ...], list[LedgerRow]] = {}
    for r in ledger:
        journals.setdefault(journal_key(r), []).append(r)
    out: dict[str, str] = {}
    for line in lines:
        guessed = (
            line.categorized_by == "MODEL"
            and unsure_below is not None
            and line.category_confidence is not None
            and line.category_confidence < unsure_below
        )
        if line.categorized_by == "USER" or (line.category not in ("", "UNKNOWN") and not guessed):
            continue
        mine = [a for a in allocations if a.status == "CONFIRMED" and line.tx_id in a.left_ids]
        if len(mine) != 1:
            continue
        money_in = line.amount > 0
        named: set[str | None] = set()
        for right in mine[0].right_ids:
            kind = kinds.get(right)
            if kind == "SALES_INVOICE":
                named.add("SALES_RECEIPT" if money_in else None)
            elif kind == "LEDGER_CASH":
                named.add(_from_booking(right, money_in, rows, journals, classifications, policy))
            else:
                named.add(None)
        category = named.pop() if len(named) == 1 else None
        if category is not None and category in policy.categories:
            out[line.tx_id] = category
    return out
