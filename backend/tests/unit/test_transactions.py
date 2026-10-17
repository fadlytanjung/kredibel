"""The Transactions table (spec 024, AC-024-6): each bank line with its category, its cash-flow
class under IFRS and US GAAP, its profit-and-loss line and subledger, the category's confidence, its
weakest reading, and the records it is matched to. Synthetic data only."""

from datetime import date
from decimal import Decimal as D
from pathlib import Path

from app.adapters.policy_files import load_category_policy, load_profit_loss_policy
from app.domain.models.bank_line import BankLine
from app.domain.models.invoice import Invoice, Receipt
from app.domain.models.match import StoredMatch
from app.domain.profit_loss import LedgerRow
from app.domain.transactions import transaction_rows

POLICY_DIR = Path(__file__).resolve().parents[3] / "contracts" / "policy"
CATEGORIES = load_category_policy(POLICY_DIR / "categories.v1.yaml", POLICY_DIR)
PNL = load_profit_loss_policy(POLICY_DIR)
AGREED = {"status": "AGREED"}


def line(tx: str, amount: str, category: str, **kw) -> BankLine:
    defaults = dict(
        tx_id=tx,
        doc_id="doc_st",
        page=1,
        row_index=int(tx[-1]),
        date=date(2026, 8, int(tx[-1])),
        month="2026-08",
        description=f"LINE {tx}",
        amount=D(amount),
        balance=None,
        category=category,
        consensus={"amount": AGREED, "date": AGREED},
    )
    return BankLine(**{**defaults, **kw})


def test_ac024_6_each_line_carries_its_classes_confidence_reading_and_records():
    lines = [
        line("st#3", "-1500000", "INTEREST_PAID", categorized_by="RULE"),
        line(
            "st#1",
            "24358950",
            "SALES_RECEIPT",
            categorized_by="MODEL",
            category_confidence=D("0.92"),
            match_state="AUTO",
        ),
        line(
            "st#2",
            "-15000000",
            "RENT",
            match_state="AUTO",
            consensus={"amount": {"status": "CONFLICT"}, "date": AGREED},
        ),
    ]
    matches = [
        StoredMatch(
            "mat_1",
            "2026-08",
            "BANK_SALES_INVOICE",
            "CONFIRMED",
            "AUTO",
            ["st#1"],
            invoice_ids=["inv_1"],
        ),
        StoredMatch(
            "mat_2",
            "2026-08",
            "BANK_LEDGER",
            "CONFIRMED",
            "AUTO",
            ["st#2"],
            ledger_entry_ids=["le_9"],
        ),
        StoredMatch(
            "mat_3", "2026-08", "BANK_RECEIPT", "REJECTED", None, ["st#3"], receipt_ids=["rc_1"]
        ),
    ]
    invoices = [
        Invoice(
            "inv_1",
            "doc_inv",
            "SALES",
            "INV/SCR/2026/08/0011",
            "Sunrise",
            "Spice Route",
            date(2026, 8, 2),
            "2026-08",
            D("24358950"),
        )
    ]
    receipts = [
        Receipt("rc_1", "doc_rc", "Swift Courier", date(2026, 8, 3), "2026-08", D("1500000"))
    ]
    ledger = [
        LedgerRow(
            entry_id="le_9",
            doc_id="doc_gl",
            row_number=2,
            date=date(2026, 8, 1),
            account_code="1110",
            account_name="Cash at bank",
            debit=D("0"),
            credit=D("15000000"),
            journal_id="BNK-2026-08-001",
            description="Warehouse rent August 2026",
        )
    ]

    rows = transaction_rows(lines, matches, invoices, receipts, ledger, CATEGORIES, PNL)

    assert [r.line.tx_id for r in rows] == ["st#1", "st#2", "st#3"]
    sale, rent, interest = rows
    assert (sale.category_label, sale.ifrs, sale.us_gaap) == (
        "Sales receipts",
        "OPERATING",
        "OPERATING",
    )
    assert (sale.pnl_line, sale.subledger, sale.confidence) == ("Revenue", "Sales", D("0.92"))
    assert sale.match_kind == "BANK_SALES_INVOICE"
    assert [(r.kind, r.record_id, r.doc_id, r.label) for r in sale.linked] == [
        ("INVOICE", "inv_1", "doc_inv", "INV/SCR/2026/08/0011")
    ]
    assert rent.reading == "CONFLICT"
    assert [(r.kind, r.doc_id, r.label) for r in rent.linked] == [
        ("LEDGER_ENTRY", "doc_gl", "BNK-2026-08-001")
    ]
    # Interest paid is financing under IFRS and operating under US GAAP; a rejected match is none.
    assert (interest.ifrs, interest.us_gaap) == ("FINANCING", "OPERATING")
    assert interest.linked == () and interest.match_kind is None and interest.confidence is None
