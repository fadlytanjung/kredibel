"""Unit tests for ledger_parse.py (Spec 005 T005-04, AC-005-10, AC-005-12)."""

from datetime import date
from decimal import Decimal

from app.domain.ledger_parse import (
    LedgerParseResult,
    compute_layout_signature,
    mask_value_shapes,
    parse_ledger_content,
)

CSV_LAYOUT_1 = """# LedgerLite 3 export
Date,Journal,Account,Account Name,Description,Reference,Debit,Credit
01/01/2026,BNK-001,6050,Warehouse rent,Rent Jan 2026,,15000000.00,
01/01/2026,BNK-001,1110,Cash at bank,Rent Jan 2026,,,15000000.00
02/01/2026,SJ-002,4000,Sales,Invoice Daybreak,,,24480000.00
"""

CSV_LAYOUT_2_SIGNED = """# Ledger export with signed amount
Posting date,Acct,Acct name,Narration,Ref,Amount
01/01/2026,6050,Warehouse rent,Rent Jan 2026,,15000000.00
01/01/2026,1110,Cash at bank,Rent Jan 2026,,-15000000.00
02/01/2026,4000,Sales,Invoice Daybreak,,-24480000.00
"""


def test_layout_signature_deterministic():
    sig1 = compute_layout_signature(["Date", "Journal", "Account", "Debit", "Credit"])
    sig2 = compute_layout_signature([" date ", "JOURNAL", "account", "debit", "credit "])
    assert sig1 == sig2
    assert len(sig1) == 40  # SHA-1 hex


def test_parse_layout1_csv_debit_credit():
    res = parse_ledger_content(CSV_LAYOUT_1, doc_id="doc_test_1", currency="IDR")
    assert isinstance(res, LedgerParseResult)
    assert len(res.rows) == 3
    assert len(res.bad_rows) == 0
    assert not res.too_many_bad_rows

    row0 = res.rows[0]
    assert row0.date == date(2026, 1, 1)
    assert row0.account_code == "6050"
    assert row0.account_name == "Warehouse rent"
    assert row0.debit == Decimal("15000000.00")
    assert row0.credit == Decimal("0")

    row1 = res.rows[1]
    assert row1.account_code == "1110"
    assert row1.credit == Decimal("15000000.00")
    assert row1.debit == Decimal("0")


def test_parse_layout2_signed_amount():
    res = parse_ledger_content(CSV_LAYOUT_2_SIGNED, doc_id="doc_test_2", currency="IDR")
    assert isinstance(res, LedgerParseResult)
    assert len(res.rows) == 3
    assert len(res.bad_rows) == 0

    # Positive amount is debit
    assert res.rows[0].account_code == "6050"
    assert res.rows[0].debit == Decimal("15000000.00")
    assert res.rows[0].credit == Decimal("0")

    # Negative amount is credit
    assert res.rows[1].account_code == "1110"
    assert res.rows[1].credit == Decimal("15000000.00")
    assert res.rows[1].debit == Decimal("0")


def test_bad_rows_and_2_percent_rule():
    # 100 rows with 1 bad row (1% <= 2% threshold)
    lines = ["Date,Account,Debit,Credit"]
    for i in range(1, 100):
        lines.append(f"01/01/2026,{1000 + i},100.00,")
    lines.append("INVALID_DATE,9999,invalid_num,")  # 1 bad row

    content_ok = "\n".join(lines)
    res_ok = parse_ledger_content(content_ok, doc_id="doc_ok", currency="IDR")
    assert len(res_ok.rows) == 99
    assert len(res_ok.bad_rows) == 1
    assert not res_ok.too_many_bad_rows

    # Now add 3 more bad rows (4 bad rows out of 103 -> ~3.8% > 2%)
    lines.append("BAD_DATE_2,8888,200.00,")
    lines.append("BAD_DATE_3,7777,300.00,")
    lines.append("BAD_DATE_4,6666,400.00,")

    content_bad = "\n".join(lines)
    res_bad = parse_ledger_content(content_bad, doc_id="doc_bad", currency="IDR")
    assert res_bad.too_many_bad_rows
    assert len(res_bad.bad_rows) == 4


def test_mask_value_shapes():
    shapes = mask_value_shapes(["2026-03-15", "INV/2026/001", "15,000,000.50", "hello@world.com"])
    assert shapes == ["9999-99-99", "AAA/9999/999", "99,999,999.99", "aaaaa@aaaaa.aaa"]
