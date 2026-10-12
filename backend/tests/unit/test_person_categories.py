"""A person's category wins (spec 007, AC-007-2; non-negotiable 17)."""

from datetime import date
from decimal import Decimal as D

from app.domain.categorize import Category, category_fits, keep_person_categories
from app.domain.models.bank_line import BankLine


def line(tx: str, category: str = "UNKNOWN", by: str = "NONE", amount: str = "-10") -> BankLine:
    return BankLine(
        tx_id=tx,
        doc_id="doc_1",
        page=1,
        row_index=1,
        date=date(2026, 3, 2),
        month="2026-03",
        description="TRANSFER OUT PRIMEPACK PACKAGING",
        amount=D(amount),
        balance=None,
        category=category,
        categorized_by=by,
        cashflow_class="OPERATING" if by != "NONE" else "UNCLASSIFIED",
    )


def test_a_statement_read_again_keeps_the_persons_categories_only():
    stored = [line("t1", "RENT", "USER"), line("t2", "BANK_FEES", "MODEL")]
    read = [line("t1"), line("t2"), line("t3")]
    kept = {
        ln.tx_id: (ln.category, ln.categorized_by) for ln in keep_person_categories(read, stored)
    }
    assert kept == {"t1": ("RENT", "USER"), "t2": ("UNKNOWN", "NONE"), "t3": ("UNKNOWN", "NONE")}
    assert read[0].cashflow_class == "OPERATING"


def test_a_category_fits_only_lines_of_its_direction():
    rent = Category("RENT", "out", "rent", "Rent", "OPERATING", "OPERATING")
    transfer = Category("INTERNAL_TRANSFER", "either", "t", "Transfer", "NON_CASH", "NON_CASH")
    assert category_fits(rent, D("-10")) and not category_fits(rent, D("10"))
    assert category_fits(transfer, D("10")) and category_fits(transfer, D("-10"))
