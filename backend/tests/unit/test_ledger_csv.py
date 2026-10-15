"""Test ledger CSV parsing (spec 018)."""

from datetime import date
from decimal import Decimal

from app.domain.ledger_csv import parse_ledger_csv

CSV_DATA = """# SYNTHETIC EXPORT
Date,Journal,Account,Account Name,Description,Reference,Debit,Credit
01/01/2026,BNK-001,6050,Warehouse rent,Rent Jan 2026,,15000000.00,
01/01/2026,BNK-001,1110,Cash at bank,Rent Jan 2026,,,15000000.00
02/01/2026,SJ-002,4000,Sales,Invoice Daybreak,,,24480000.00
"""


def test_parse_ledger_csv_converts_rows_deterministically():
    rows = parse_ledger_csv(CSV_DATA, "doc_123", currency="IDR")
    assert len(rows) == 3
    assert rows[0].entry_id == "entry_doc_123_1"
    assert rows[0].date == date(2026, 1, 1)
    assert rows[0].account_code == "6050"
    assert rows[0].account_name == "Warehouse rent"
    assert rows[0].debit == Decimal("15000000.00")
    assert rows[0].credit == Decimal("0")
    assert rows[0].currency == "IDR"
    assert rows[0].posting_status == "POSTED"

    assert rows[2].account_code == "4000"
    assert rows[2].credit == Decimal("24480000.00")
    assert rows[2].debit == Decimal("0")
