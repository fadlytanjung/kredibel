"""Statements that print the date once per day (docs/07 §7): a row with its own amount and a blank
date cell is a transaction of the day above, not a wrapped description. Synthetic data only."""

from datetime import date
from decimal import Decimal

from app.domain.layout import chunk_page
from app.domain.reading import (
    StatementHeader,
    StatementPageReading,
    StatementRowReading,
    build_statement,
)
from tests.unit.test_layout import _line

COLUMNS = (
    ("Date", 0.05),
    ("Description", 0.15),
    ("Debit", 0.55),
    ("Credit", 0.70),
    ("Balance", 0.85),
)
PAGE = [
    *_line(0.10, ("Period 01/03/2026 - 31/03/2026", 0.05)),
    *_line(0.20, *COLUMNS),
    *_line(
        0.23,
        ("05/03/2026", 0.05),
        ("SETORAN TUNAI", 0.15),
        ("1,000,000.00", 0.70),
        ("1,500,000.00", 0.85),
    ),
    *_line(0.25, ("PPH JASA", 0.15), ("20,000.00", 0.55), ("1,480,000.00", 0.85)),
    *_line(0.27, ("BIAYA ADM", 0.15), ("5,000.00", 0.55), ("1,475,000.00", 0.85)),
    *_line(
        0.29,
        ("06/03/2026", 0.05),
        ("TRK TUNAI", 0.15),
        ("475,000.00", 0.55),
        ("1,000,000.00", 0.85),
    ),
]


def _row(n: int, date_text: str, description: str, debit=None, credit=None, balance=None):
    return StatementRowReading(
        row_on_page=n,
        date_text=date_text,
        description=description,
        debit_text=debit,
        credit_text=credit,
        balance_text=balance,
    )


def _build(rows: list[StatementRowReading]):
    page = StatementPageReading(
        page=1,
        header=StatementHeader(
            bank_name="Synthetic Bank",
            currency="IDR",
            period_start_text="01/03/2026",
            period_end_text="31/03/2026",
            column_order=["date", "description", "debit", "credit", "balance"],
        ),
        rows=rows,
    )
    return build_statement("doc_1", [page], {1: chunk_page(PAGE, page=1)})


def test_a_row_with_an_amount_and_no_printed_date_takes_the_date_above():
    result = _build(
        [
            _row(0, "05/03/2026", "SETORAN TUNAI", credit="1,000,000.00", balance="1,500,000.00"),
            _row(1, "", "PPH JASA", debit="20,000.00", balance="1,480,000.00"),
            _row(2, "", "BIAYA ADM", debit="5,000.00", balance="1,475,000.00"),
            _row(3, "06/03/2026", "TRK TUNAI", debit="475,000.00", balance="1,000,000.00"),
        ]
    )

    assert [line.date for line in result.lines] == [
        date(2026, 3, 5),
        date(2026, 3, 5),
        date(2026, 3, 5),
        date(2026, 3, 6),
    ]
    assert [line.amount for line in result.lines] == [
        Decimal("1000000.00"),
        Decimal("-20000.00"),
        Decimal("-5000.00"),
        Decimal("-475000.00"),
    ]
    balances = [line.balance for line in result.lines]
    for before, line, after in zip(balances, result.lines[1:], balances[1:], strict=False):
        assert before is not None and after is not None and before + line.amount == after


def test_a_first_row_without_a_date_has_no_day_to_take_and_is_noted():
    result = _build([_row(0, "", "PPH JASA", debit="20,000.00", balance="1,480,000.00")])
    assert result.lines == []
    assert any("row 0" in note for note in result.notes)
