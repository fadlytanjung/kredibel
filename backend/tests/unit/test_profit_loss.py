"""Synthetic posted journals: AC-018-3/4 (no cash/invoice double counting)."""

from datetime import date
from decimal import Decimal as D
from itertools import permutations
from pathlib import Path

from app.adapters.policy_files import load_profit_loss_policy
from app.domain.profit_loss import Classification, LedgerRow, build_profit_loss

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
