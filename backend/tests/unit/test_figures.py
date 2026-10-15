"""Month figures as facts (spec 007, T007-06, AC-007-9; docs/08 §5; ADR-025): synthetic inputs."""

from datetime import date
from decimal import Decimal as D
from pathlib import Path

import yaml

from app.domain.categorize import parse_category_policy
from app.domain.figures import AccountLines, month_figures
from app.domain.models.bank_line import BankLine
from app.domain.models.invoice import Invoice, Receipt
from app.domain.reconcile import Allocation

POLICY_DIR = Path(__file__).resolve().parents[3] / "contracts" / "policy"
CATEGORIES = parse_category_policy(
    yaml.safe_load((POLICY_DIR / "categories.v1.yaml").read_text()),
    yaml.safe_load((POLICY_DIR / "categorization-rules.v1.yaml").read_text()),
)


def _line(tx: str, day: int, amount: str, balance: str, category: str, cls: str) -> BankLine:
    return BankLine(
        tx_id=tx,
        doc_id="doc_s",
        page=1,
        row_index=day,
        date=date(2026, 3, day),
        month="2026-03",
        description=tx,
        amount=D(amount),
        balance=D(balance),
        category=category,
        cashflow_class=cls,
    )


LINES = [
    _line("t1", 2, "1000.00", "1100.00", "SALES_RECEIPT", "OPERATING"),
    _line("t2", 5, "-300.00", "800.00", "RENT", "OPERATING"),
    _line("t3", 6, "-900.00", "-100.00", "LOAN_REPAYMENT", "FINANCING"),
    _line("t4", 7, "200.00", "100.00", "INTERNAL_TRANSFER", "NON_CASH"),
    _line("t5", 9, "-50.00", "50.00", "UNKNOWN", "UNCLASSIFIED"),
]


def _alloc(left: tuple[str, ...], status: str, method: str | None) -> Allocation:
    return Allocation(f"mch_{left[0]}", left, ("i1",), status, method, D("0.9"), (), D(0), False)  # type: ignore[arg-type]


def _facts(allocations=(), invoices=(), receipts=()):
    return month_figures(
        "2026-03",
        [AccountLines("RHB ••••3876", LINES)],
        list(invoices),
        list(receipts),
        CATEGORIES,
        list(allocations),
    )


def test_cash_totals_leave_out_non_cash_lines():
    f = _facts()
    assert (f["money_in"].value, f["money_out"].value, f["net"].value) == (
        "1000.00",
        "1250.00",
        "-250.00",
    )
    assert (f["operating_in"].value, f["operating_out"].value) == ("1000.00", "300.00")
    assert f["money_in"].inputs == ("t1",) and set(f["money_out"].inputs) == {"t2", "t3", "t5"}
    assert f["net"].inputs == ("fact:2026-03:money_in", "fact:2026-03:money_out")
    assert f["money_in"].fact_id == "fact:2026-03:money_in"


def test_balances_and_negative_days_come_from_the_printed_balances():
    f = _facts()
    assert (f["opening"].value, f["closing"].value, f["negative_days"].value) == (
        "100.00",
        "50.00",
        "1",
    )


def test_balances_add_up_over_accounts():
    other = [_line("u1", 3, "10.00", "510.00", "SALES_RECEIPT", "OPERATING")]
    f = month_figures(
        "2026-03", [AccountLines("A", LINES), AccountLines("B", other)], [], [], CATEGORIES, []
    )
    assert (f["opening"].value, f["closing"].value) == ("600.00", "560.00")


def test_match_states_count_support_without_judging_unsupported_lines():
    f = _facts(
        [
            _alloc(("t1",), "CONFIRMED", "AUTO"),
            _alloc(("t2",), "CONFIRMED", "MANUAL"),
            _alloc(("t3",), "PROPOSED", None),
        ]
    )
    counts = {
        k: f[k].value
        for k in (
            "bank_lines",
            "auto_matched",
            "manually_matched",
            "proposed",
            "unmatched",
            "excluded",
        )
    }
    assert counts == {
        "bank_lines": "5",
        "auto_matched": "1",
        "manually_matched": "1",
        "proposed": "1",
        "unmatched": "1",
        "excluded": "1",
    }
    assert f["auto_match_rate"].value == "0.2500"  # 1 of the 4 lines that are cash flows


def test_document_totals_and_categories():
    inv = Invoice(
        "inv_1",
        "doc_i",
        "SALES",
        "INV-1",
        "Me",
        "Client",
        date(2026, 3, 1),
        "2026-03",
        D("1000.00"),
    )
    buy = Invoice(
        "inv_2",
        "doc_p",
        "PURCHASE",
        "P-1",
        "Supplier",
        "Me",
        date(2026, 3, 1),
        "2026-03",
        D("300.00"),
    )
    rcp = Receipt("rcp_1", "doc_r", "Kedai", date(2026, 3, 4), "2026-03", D("12.50"))
    f = _facts(invoices=[inv, buy], receipts=[rcp])
    assert (
        f["invoiced_sales"].value,
        f["invoiced_purchases"].value,
        f["receipts_total"].value,
    ) == (
        "1000.00",
        "300.00",
        "12.50",
    )
    assert f["category:RENT"].value == "-300.00" and f["line:FINANCING"].value == "-900.00"
    assert f["uncategorized"].value == "1"
