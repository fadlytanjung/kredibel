"""Synthetic posted journals: AC-018-3/4 (no cash/invoice double counting); and the cash basis from
categorized bank lines while no ledger export exists: AC-018-8."""

from datetime import date
from decimal import Decimal as D
from itertools import permutations
from pathlib import Path

from app.adapters.policy_files import load_category_policy, load_profit_loss_policy
from app.domain.models.bank_line import BankLine
from app.domain.profit_loss import (
    Classification,
    LedgerRow,
    build_cash_profit_loss,
    build_profit_loss,
)

POLICY_DIR = Path(__file__).resolve().parents[3] / "contracts/policy"


def row(code: str, debit: str = "0", credit: str = "0", **kw) -> LedgerRow:
    return LedgerRow(
        entry_id=kw.pop("entry_id", code),
        doc_id="doc_synthetic",
        row_number=1,
        date=date(2026, 3, 2),
        account_code=code,
        account_name=code,
        debit=D(debit),
        credit=D(credit),
        currency="IDR",
        posting_status="POSTED",
        journal_id="j1",
        **kw,
    )


def mappings():
    return {
        "sales": Classification(account_code="sales", pnl_line="REVENUE", subledger="RECEIVABLES"),
        "cost": Classification(
            account_code="cost", pnl_line="COST_OF_SALES", subledger="INVENTORY"
        ),
        "rent": Classification(
            account_code="rent", pnl_line="OPERATING_EXPENSES", subledger="PAYABLES"
        ),
        "bank": Classification(account_code="bank", pnl_line="BALANCE_SHEET", subledger="CASH"),
    }


def report(rows, classes=None):
    return build_profit_loss(
        rows,
        mappings() if classes is None else classes,
        load_profit_loss_policy(POLICY_DIR),
        currency="IDR",
        period="2026-03",
    )


def test_ac018_3_signed_profit_and_source_rows_are_order_independent():
    rows = [
        row("sales", credit="100.10"),
        row("cost", debit="30.02"),
        row("rent", debit="10.01"),
        row("bank", debit="60.07"),
    ]
    expected = report(rows)
    amounts = {x.id: x.amount for x in expected.lines}
    assert amounts["REVENUE"] == D("100.10")
    assert amounts["GROSS_PROFIT"] == D("70.08")
    assert amounts["NET_PROFIT"] == D("60.07")
    assert expected.status == "IMPORTED"
    assert expected.lines[0].entry_ids == ["sales"]
    assert expected.entries[0].doc_id == "doc_synthetic"
    for order in permutations(rows):
        assert report(list(order)) == expected


def test_ac018_4_refunds_reduce_revenue_and_unmapped_never_becomes_expense():
    rows = [row("sales", debit="5.11"), row("bank", credit="5.11")]
    assert report(rows).lines[-1].amount == D("-5.11")
    partial = report(rows, {})
    assert partial.status == "PARTIAL"
    assert partial.exclusions["UNCLASSIFIED"] == 2
    assert partial.lines[-1].amount is None  # no classified P&L evidence


def test_ac018_4_empty_drafts_held_foreign_and_closing_are_not_profit():
    assert report([]).status == "UNAVAILABLE"
    assert report([]).lines[-1].amount is None
    rows = [row("sales", credit="10"), row("bank", debit="10")]
    for field, value, reason in [
        ("posting_status", "DRAFT", "NOT_POSTED"),
        ("held_as_duplicate", True, "HELD_DUPLICATE"),
        ("currency", "USD", "CURRENCY"),
        ("entry_kind", "CLOSING", "NON_ACTIVITY"),
    ]:
        altered = [r.model_copy(update={field: value}) for r in rows]
        found = report(altered)
        assert found.status == "UNAVAILABLE"
        assert found.exclusions[reason] == 2
        assert found.lines[-1].amount is None


def test_ac018_4_unbalanced_journal_is_a_visible_gap_and_no_silent_deduplication():
    found = report([row("sales", credit="100")])
    assert found.status == "PARTIAL"
    assert "UNBALANCED_JOURNAL" in found.gaps
    assert found.lines[-1].amount == D("100")
    duplicate = report([row("sales", credit="100"), row("sales", credit="100")])
    assert duplicate.status == "UNAVAILABLE"
    assert duplicate.lines[-1].amount is None
    assert duplicate.exclusions["DUPLICATE_ENTRY_ID"] == 2


CATEGORIES = load_category_policy(POLICY_DIR / "categories.v1.yaml", POLICY_DIR)


def line(tx: str, amount: str, category: str, *, day: int = 2, doc: str = "doc_stmt") -> BankLine:
    return BankLine(
        tx_id=tx,
        doc_id=doc,
        page=1,
        row_index=int(tx[-1]) if tx[-1].isdigit() else 0,
        date=date(2026, 3, day),
        month="2026-03",
        description=tx.upper(),
        amount=D(amount),
        balance=None,
        category=category,
    )


def cash(lines, **kw):
    return build_cash_profit_loss(
        lines,
        CATEGORIES,
        load_profit_loss_policy(POLICY_DIR),
        currency="IDR",
        period="2026-03",
        **kw,
    )


def test_ac018_8_cash_basis_lines_follow_the_category_labels_and_are_order_independent():
    lines = [
        line("tx1", "100.10", "SALES_RECEIPT"),
        line("tx2", "-30.02", "INVENTORY_PURCHASE"),
        line("tx3", "-10.01", "RENT"),
        line("tx4", "-60.07", "LOAN_REPAYMENT"),  # balance sheet: never an expense
        line("tx5", "-5.00", "INTERNAL_TRANSFER"),  # not a cash flow of the business
        line("tx6", "-7.00", "UNKNOWN"),  # waits for a category: the report is partial
    ]
    expected = cash(lines)
    amounts = {x.id: x.amount for x in expected.lines}
    assert expected.basis == "CASH" and expected.coverage == "BANK_LINES_ONLY"
    assert amounts["REVENUE"] == D("100.10")
    assert amounts["COST_OF_SALES"] == D("30.02")
    assert amounts["GROSS_PROFIT"] == D("70.08")
    assert amounts["OPERATING_EXPENSES"] == D("10.01")
    assert amounts["NET_PROFIT"] == D("60.07")
    assert expected.status == "PARTIAL"
    assert expected.exclusions == {"NOT_CASH_FLOW": 1, "UNCATEGORIZED": 1}
    assert expected.gaps == ["NO_LEDGER_EXPORT"]
    assert expected.classified_count == 4 and expected.input_count == 6
    by_id = {e.entry_id: e for e in expected.entries}
    assert by_id["tx2"].subledger == "PURCHASES" and by_id["tx3"].subledger == "OCCUPANCY"
    assert by_id["tx1"].account_name == "Sales receipts"
    assert "tx4" not in by_id
    for order in permutations(lines):
        assert cash(list(order)) == expected


def test_ac018_8_a_refund_reverses_its_own_line_and_a_held_statement_is_excluded():
    refunds = cash([line("tx1", "-5.11", "SALES_RECEIPT"), line("tx2", "3.00", "RENT")])
    amounts = {x.id: x.amount for x in refunds.lines}
    assert amounts["REVENUE"] == D("-5.11") and amounts["OPERATING_EXPENSES"] == D("-3.00")
    assert refunds.status == "IMPORTED"
    held = cash(
        [
            line("tx1", "100.00", "SALES_RECEIPT"),
            line("tx2", "100.00", "SALES_RECEIPT", doc="doc_copy"),
        ],
        excluded_docs={"doc_copy": "HELD_DUPLICATE"},
    )
    assert {x.id: x.amount for x in held.lines}["REVENUE"] == D("100.00")
    assert held.exclusions == {"HELD_DUPLICATE": 1}


def test_ac018_8_only_the_period_s_lines_count_and_nothing_means_unavailable():
    april = line("tx9", "50.00", "SALES_RECEIPT")
    april = BankLine(**{**april.__dict__, "date": date(2026, 4, 1), "month": "2026-04"})
    report = cash([line("tx1", "20.00", "SALES_RECEIPT"), april])
    assert report.input_count == 1 and {x.id: x.amount for x in report.lines}["REVENUE"] == D(
        "20.00"
    )
    empty = cash([april])
    assert empty.status == "UNAVAILABLE" and all(x.amount is None for x in empty.lines)
