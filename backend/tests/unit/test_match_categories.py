"""A line nothing categorized takes its category from what it is matched to (spec 023, AC-023-12):
a sales invoice is a sales receipt; a ledger booking is what its other account is classified as,
when that names one category. A category a person or a rule set is never replaced, nor one the
reading was sure of; a reading's guess that still needs a check gives way to the match. An
ambiguous booking leaves the line as it is. Synthetic data only."""

from datetime import date
from decimal import Decimal as D
from pathlib import Path
from typing import Literal

from app.adapters.policy_files import load_category_policy
from app.domain.match_categories import categories_from_matches
from app.domain.models.bank_line import BankLine
from app.domain.profit_loss import Classification, LedgerRow
from app.domain.reconcile import Allocation

POLICY_DIR = Path(__file__).resolve().parents[3] / "contracts" / "policy"
CATEGORIES = load_category_policy(POLICY_DIR / "categories.v1.yaml", POLICY_DIR)


def line(
    tx: str, amount: str, category: str = "UNKNOWN", by: str = "NONE", sure: str | None = None
) -> BankLine:
    return BankLine(
        tx,
        "doc_st",
        1,
        int(tx[-1]),
        date(2026, 8, 4),
        "2026-08",
        f"LINE {tx}",
        D(amount),
        None,
        category=category,
        categorized_by=by,
        category_confidence=D(sure) if sure else None,
    )


def booking(entry: str, journal: str, code: str, debit: str = "0", credit: str = "0") -> LedgerRow:
    return LedgerRow(
        entry_id=entry,
        doc_id="doc_gl",
        row_number=int(entry[-1]),
        date=date(2026, 8, 4),
        account_code=code,
        account_name=code,
        debit=D(debit),
        credit=D(credit),
        journal_id=journal,
    )


def matched(
    tx: str, right: str, status: Literal["CONFIRMED", "PROPOSED"] = "CONFIRMED"
) -> Allocation:
    return Allocation(
        f"mat_{tx}",
        (tx,),
        (right,),
        status,
        "AUTO" if status == "CONFIRMED" else None,
        D("0.9"),
        ("AMOUNT_EXACT",),
        D(0),
        False,
    )


CLASSES = {
    "4100": Classification(account_code="4100", pnl_line="REVENUE", subledger="CASH"),
    "6000": Classification(account_code="6000", pnl_line="OPERATING_EXPENSES", subledger="PAYROLL"),
    "6100": Classification(account_code="6100", pnl_line="OPERATING_EXPENSES", subledger="CASH"),
    "3100": Classification(account_code="3100", pnl_line="BALANCE_SHEET", subledger="GENERAL"),
    "2200": Classification(account_code="2200", pnl_line="BALANCE_SHEET", subledger="RECEIVABLES"),
}


def test_a_line_takes_the_category_its_match_names():
    lines = [
        line("st#1", "2500000"),  # cash deposit booked to retail sales (with VAT)
        line("st#2", "-44100000"),  # payroll booked to salaries
        line("st#3", "24358950"),  # paid a sales invoice
        line("st#4", "-150000"),  # booked to an expense account several categories share
        line(
            "st#5", "5000000"
        ),  # owner money: a balance-sheet account says nothing about the category
        line("st#6", "1750000", "OWNER_CAPITAL", "USER"),  # a person decided
        line("st#7", "1200000", "SALES_RECEIPT", "MODEL"),  # the reading decided
        line("st#8", "900000"),  # only a proposal
    ]
    ledger = [
        booking("le#1", "J1", "1110", debit="2500000"),
        booking("le#2", "J1", "4100", credit="2272727"),
        booking("le#3", "J1", "2200", credit="227273"),
        booking("le#4", "J2", "1110", credit="44100000"),
        booking("le#5", "J2", "6000", debit="44100000"),
        booking("le#6", "J4", "1110", credit="150000"),
        booking("le#7", "J4", "6100", debit="150000"),
        booking("le#8", "J5", "1110", debit="5000000"),
        booking("le#9", "J5", "3100", credit="5000000"),
    ]
    allocations = [
        matched("st#1", "le#1"),
        matched("st#2", "le#4"),
        matched("st#3", "inv_1"),
        matched("st#4", "le#6"),
        matched("st#5", "le#8"),
        matched("st#6", "le#1"),
        matched("st#7", "inv_2"),
        matched("st#8", "inv_3", status="PROPOSED"),
    ]
    kinds = {
        "le#1": "LEDGER_CASH",
        "le#4": "LEDGER_CASH",
        "le#6": "LEDGER_CASH",
        "le#8": "LEDGER_CASH",
        "inv_1": "SALES_INVOICE",
        "inv_2": "SALES_INVOICE",
        "inv_3": "SALES_INVOICE",
    }

    found = categories_from_matches(lines, allocations, kinds, ledger, CLASSES, CATEGORIES)

    assert found == {"st#1": "SALES_RECEIPT", "st#2": "PAYROLL", "st#3": "SALES_RECEIPT"}


def test_a_match_replaces_a_reading_guess_that_needs_a_check():
    """Spec 024: a cash deposit the reading guessed was the owner's money (50% sure, below the
    learning policy's 0.70 for a category check) is booked to retail sales: the match decides."""
    lines = [
        line("st#1", "2500000", "OWNER_CAPITAL", "MODEL", sure="0.5"),  # a guess
        line("st#2", "2500000", "OWNER_CAPITAL", "MODEL", sure="0.9"),  # the reading was sure
        line("st#3", "2500000", "OWNER_CAPITAL", "RULE"),  # a rule decided
        line("st#4", "2500000", "OWNER_CAPITAL", "USER"),  # a person decided
    ]
    ledger: list[LedgerRow] = []
    for n in "1234":
        ledger += [
            booking(f"le#{n}", f"J{n}", "1110", debit="2500000"),
            booking(f"lr#{n}", f"J{n}", "4100", credit="2500000"),
        ]
    allocations = [matched(f"st#{n}", f"le#{n}") for n in "1234"]
    kinds = {f"le#{n}": "LEDGER_CASH" for n in "1234"}

    found = categories_from_matches(
        lines, allocations, kinds, ledger, CLASSES, CATEGORIES, unsure_below=D("0.70")
    )

    assert found == {"st#1": "SALES_RECEIPT"}
