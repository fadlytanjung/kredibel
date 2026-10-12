"""From grounded pages to bank lines and statement metadata (docs/07 §5.2, §7, §8; AC-005-7)."""

from datetime import date
from decimal import Decimal

from app.domain.layout import chunk_page
from app.domain.reading import (
    StatementHeader,
    StatementPageReading,
    StatementRowReading,
    StatementTotals,
    build_statement,
)
from tests.unit.test_layout import _line

PAGE1 = [
    *_line(0.10, ("Statement Period: 16 Aug 26 - 15 Sep 26", 0.06)),
    *_line(
        0.20,
        ("Date", 0.06),
        ("Description", 0.15),
        ("Debit", 0.62),
        ("Credit", 0.74),
        ("Balance", 0.88),
    ),
    *_line(0.23, ("16Aug", 0.06), ("B/FBALANCE", 0.15), ("1,216.73", 0.88)),
    *_line(
        0.26,
        ("16Aug", 0.06),
        ("DEBITCARDTXN-DR", 0.15),
        ("3001234567", 0.45),
        ("12.40", 0.64),
        ("1,204.33", 0.88),
    ),
    *_line(0.273, ("123456 GRABRIDES-", 0.15)),
]
PAGE2 = [
    *_line(
        0.20,
        ("Date", 0.06),
        ("Description", 0.15),
        ("Debit", 0.62),
        ("Credit", 0.74),
        ("Balance", 0.88),
    ),
    *_line(0.23, ("02Sep", 0.06), ("MBKINSTANTTRFCR", 0.15), ("250.00", 0.75), ("1,454.33", 0.88)),
    *_line(0.243, ("NURUL AINA", 0.15)),
    *_line(0.27, ("15Sep", 0.06), ("C/FBALANCE", 0.15), ("1,454.33", 0.88)),
]


def _reading():
    p1 = StatementPageReading(
        page=1,
        header=StatementHeader(
            bank_name="RHB Bank Berhad",
            account_holder="NUR AMIRA BINTI ZAKI",
            account_number="21446400012345",
            holder_address=None,
            currency="RM",
            period_start_text="16 Aug 26",
            period_end_text="15 Sep 26",
            opening_balance_text=None,
            column_order=["date", "description", "debit", "credit", "balance"],
        ),
        rows=[
            StatementRowReading(
                row_on_page=0,
                date_text="16 Aug",
                description="B/F BALANCE",
                balance_text="1,216.73",
            ),
            StatementRowReading(
                row_on_page=1,
                date_text="16 Aug",
                description="DEBIT CARD TXN-DR\n123456 GRAB RIDES-",
                debit_text="12.40",
                balance_text="1,204.33",
            ),
        ],
    )
    p2 = StatementPageReading(
        page=2,
        rows=[
            StatementRowReading(
                row_on_page=0,
                date_text="02 Sep",
                description="MBK INSTANT TRF CR\nNURUL AINA",
                credit_text="250.00",
                balance_text="1,454.33",
            ),
            StatementRowReading(
                row_on_page=1,
                date_text="15 Sep",
                description="C/F BALANCE",
                balance_text="1,454.33",
            ),
        ],
        totals=StatementTotals(
            total_debits_text="12.40", total_credits_text="250.00", closing_balance_text=None
        ),
    )
    return [p1, p2], {1: chunk_page(PAGE1, page=1), 2: chunk_page(PAGE2, page=2)}


def test_rows_become_bank_lines_with_signed_amounts_and_dates_in_the_period():
    result = build_statement("doc_1", *_reading())
    lines = result.lines
    assert [(ln.date, ln.amount, ln.balance) for ln in lines] == [
        (date(2026, 8, 16), Decimal("-12.40"), Decimal("1204.33")),
        (date(2026, 9, 2), Decimal("250.00"), Decimal("1454.33")),
    ]
    assert [ln.month for ln in lines] == ["2026-08", "2026-09"]
    assert lines[0].tx_id.startswith("tx_") and lines[0].tx_id != lines[1].tx_id
    assert lines[0].counterparty_name == "GRAB RIDES"
    assert lines[1].counterparty_name == "NURUL AINA"
    assert [ln.row_index for ln in lines] == [1, 2]


def test_every_value_keeps_its_grounding():
    line = build_statement("doc_1", *_reading()).lines[0]
    assert line.consensus["amount"]["status"] == "AGREED"
    assert line.consensus["amount"]["raw"] == {"GEMINI": "12.40", "TEXT_LAYER": "12.40"}
    assert line.consensus["amount"]["bbox"] is not None
    assert line.consensus["date"]["page"] == 1


def test_statement_meta_comes_from_header_and_balance_lines():
    meta = build_statement("doc_1", *_reading()).meta
    assert (meta.period_start, meta.period_end) == (date(2026, 8, 16), date(2026, 9, 15))
    assert (meta.opening, meta.closing) == (Decimal("1216.73"), Decimal("1454.33"))
    assert meta.account_masked == "••••2345"
    assert meta.currency == "MYR"
    assert meta.bank_name == "RHB Bank Berhad"


def test_reading_summary_and_months():
    result = build_statement("doc_1", *_reading())
    assert result.months == ["2026-08", "2026-09"]
    assert result.agreement == 1.0
    assert result.fields_compared > 0


def test_balances_follow_the_running_equation_check_input():
    """Opening + credits - debits = closing on this statement; the check itself is spec 006."""
    result = build_statement("doc_1", *_reading())
    assert result.meta.opening is not None
    total = result.meta.opening + sum(ln.amount for ln in result.lines)
    assert total == result.meta.closing
