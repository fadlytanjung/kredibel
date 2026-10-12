"""Month checks (spec 007, T007-07, AC-007-10, AC-007-11; docs/08 §2.2, §2.6, §2.7); synthetic.

X09 waits for ledger import (spec 005 T005-04/09)."""

from dataclasses import replace
from datetime import date
from decimal import Decimal as D
from pathlib import Path
from typing import Literal

import pytest

from app.adapters.policy_files import load_forensics, load_reconciliation_policy
from app.domain.checks.month import MonthContext, StatementSpan, run_month_checks
from app.domain.models.bank_line import BankLine
from app.domain.models.invoice import Invoice
from app.domain.reconcile import Allocation

POLICY_DIR = Path(__file__).resolve().parents[3] / "contracts" / "policy"
FORENSICS = load_forensics(POLICY_DIR)
FORENSICS = FORENSICS.model_copy(update={"enabled": FORENSICS.enabled})
RECON = load_reconciliation_policy(POLICY_DIR)
ACC = "Archipelago Commerce Bank ••••4821"


def line(
    tx: str, day: date, amount: str, desc: str, balance: str | None = "100.00", tags=()
) -> BankLine:
    return BankLine(
        tx_id=tx,
        doc_id="doc_mar",
        page=1,
        row_index=day.day,
        date=day,
        month=f"{day:%Y-%m}",
        description=desc,
        amount=D(amount),
        balance=None if balance is None else D(balance),
        risk_tags=list(tags),
    )


def span(doc: str, start: date, end: date, opening: str, closing: str) -> StatementSpan:
    return StatementSpan(doc, ACC, start, end, D(opening), D(closing))


def invoice(
    iid: str,
    kind: Literal["SALES", "PURCHASE"],
    issued: date,
    total: str,
    issuer: str,
    buyer: str,
    pay_to=None,
) -> Invoice:
    return Invoice(
        iid,
        f"doc_{iid}",
        kind,
        iid.upper(),
        issuer,
        buyer,
        issued,
        f"{issued:%Y-%m}",
        D(total),
        currency="IDR",
        due_date=issued.replace(day=min(issued.day + 14, 28)),
        pay_to_masked=pay_to,
    )


def ctx(month: str = "2026-03", **kw) -> MonthContext:
    base = dict(
        month=month,
        policy=FORENSICS,
        reconciliation=RECON,
        workspace_currency="IDR",
        statements=[span("doc_mar", date(2026, 3, 1), date(2026, 3, 31), "1000.00", "500.00")],
        lines=[],
        all_lines=[],
        invoices=[],
        receipts=[],
        allocations=[],
        negative_days=0,
        own_names=["Sunrise Coffee Roasters"],
    )
    return MonthContext(**{**base, **kw})


def codes(findings) -> dict[str, str]:
    return {f.code: f.severity for f in findings}


def test_a_clean_month_has_no_findings():
    assert run_month_checks(ctx()) == []


def test_x01_a_closing_balance_that_the_next_statement_does_not_open_with():
    statements = [
        span("doc_feb", date(2026, 2, 1), date(2026, 2, 28), "900.00", "1000.00"),
        span("doc_mar", date(2026, 3, 1), date(2026, 3, 31), "1250.00", "500.00"),
    ]
    [f] = run_month_checks(ctx(statements=statements))
    assert (f.code, f.severity, f.month) == ("X01_STATEMENT_DISCONTINUITY", "HIGH", "2026-03")
    assert (f.facts["previousClosing"], f.facts["opening"]) == ("1000.00", "1250.00")
    assert {e.doc_id for e in f.evidence} == {"doc_feb", "doc_mar"}
    joined = [
        span("doc_feb", date(2026, 2, 1), date(2026, 2, 28), "900.00", "1000.00"),
        span("doc_mar", date(2026, 3, 1), date(2026, 3, 31), "1000.00", "500.00"),
    ]
    assert run_month_checks(ctx(statements=joined)) == []


def test_x02_a_month_between_statements_without_one():
    statements = [
        span("doc_jan", date(2026, 1, 1), date(2026, 1, 31), "900.00", "1000.00"),
        span("doc_mar", date(2026, 3, 1), date(2026, 3, 31), "1000.00", "500.00"),
    ]
    [f] = run_month_checks(ctx("2026-02", statements=statements))
    assert (f.code, f.severity, f.facts["account"]) == ("X02_STATEMENT_MISSING", "MEDIUM", ACC)
    assert (
        run_month_checks(ctx("2026-03", statements=statements)) == []
    )  # X01 needs adjacent periods


def test_behaviour_gambling_returned_items_and_negative_days():
    lines = [
        line("t1", date(2026, 3, 3), "-50", "SLOT GAMES 88", tags=["GAMBLING"]),
        *[
            line(f"r{i}", date(2026, 3, 4 + i), "-10", "RETURNED CHEQUE", tags=["RETURNED_ITEM"])
            for i in range(3)
        ],
    ]
    found = codes(run_month_checks(ctx(lines=lines, negative_days=4)))
    assert found == {
        "B01_GAMBLING_INDICATORS": "MEDIUM",
        "B04_RETURNED_ITEMS": "HIGH",
        "C02_NEGATIVE_BALANCE_DAYS": "MEDIUM",
    }
    one = codes(run_month_checks(ctx(lines=lines[:2], negative_days=2)))
    assert one == {"B01_GAMBLING_INDICATORS": "MEDIUM", "B04_RETURNED_ITEMS": "MEDIUM"}


def _paid(left: str, right: str) -> Allocation:
    return Allocation(
        f"mch_{left}", (left,), (right,), "CONFIRMED", "AUTO", D("0.95"), (), D(0), False
    )


def test_d07_a_second_debit_for_an_invoice_already_paid():
    bill = invoice(
        "p1",
        "PURCHASE",
        date(2026, 3, 2),
        "250.00",
        "PrimePack Packaging",
        "Sunrise Coffee Roasters",
    )
    lines = [
        line("d1", date(2026, 3, 5), "-250.00", "TRANSFER OUT PRIMEPACK PACKAGING"),
        line("d2", date(2026, 3, 9), "-250.00", "TRANSFER OUT PRIMEPACK PACKAGING"),
    ]
    [f] = run_month_checks(
        ctx(lines=lines, all_lines=lines, invoices=[bill], allocations=[_paid("d1", "p1")])
    )
    assert (f.code, f.severity, f.facts["secondPayment"]) == ("D07_DOUBLE_PAYMENT", "HIGH", "d2")


def test_r01_an_overdue_sales_invoice_only_where_statements_cover_the_period():
    sale = invoice(
        "s1", "SALES", date(2026, 1, 5), "1000.00", "Sunrise Coffee Roasters", "Daybreak Café"
    )
    covered = [
        span("doc_jan", date(2026, 1, 1), date(2026, 1, 31), "0", "0"),
        span("doc_feb", date(2026, 2, 1), date(2026, 2, 28), "0", "0"),
        span("doc_mar", date(2026, 3, 1), date(2026, 3, 31), "0", "0"),
    ]
    found = run_month_checks(ctx("2026-02", statements=covered, invoices=[sale]))
    assert codes(found) == {"R01_SALES_INVOICE_OVERDUE": "MEDIUM"}  # the month's only sale
    gap = [covered[0], covered[2]]
    assert "R01_SALES_INVOICE_OVERDUE" not in codes(
        run_month_checks(ctx("2026-02", statements=gap, invoices=[sale]))
    )
    paid = run_month_checks(
        ctx("2026-02", statements=covered, invoices=[sale], allocations=[_paid("c1", "s1")])
    )
    assert paid == []


def test_r02_a_supplier_with_no_bank_history_never_paid():
    bill = invoice(
        "p9",
        "PURCHASE",
        date(2026, 3, 4),
        "800.00",
        "Bluewater Trading Co.",
        "Sunrise Coffee Roasters",
    )
    [f] = run_month_checks(ctx(invoices=[bill]))
    assert (f.code, f.severity) == ("R02_SUPPLIER_INVOICE_UNKNOWN_PARTY", "MEDIUM")
    known = [line("k1", date(2026, 1, 9), "-100", "TRANSFER OUT BLUEWATER TRADING CO")]
    assert run_month_checks(ctx(invoices=[bill], all_lines=known)) == []


def test_x08_a_supplier_asks_to_be_paid_into_a_new_account():
    old = invoice(
        "p1", "PURCHASE", date(2026, 1, 4), "250.00", "PrimePack Packaging", "Me", pay_to="••••1111"
    )
    new = invoice(
        "p2", "PURCHASE", date(2026, 3, 4), "250.00", "PRIMEPACK PACKAGING", "Me", pay_to="••••9999"
    )
    history = [line("h1", date(2026, 1, 9), "-250.00", "TRANSFER OUT PRIMEPACK PACKAGING")]
    [f] = run_month_checks(
        ctx(invoices=[old, new], all_lines=history, allocations=[_paid("h9", "p2")])
    )
    assert (f.code, f.severity) == ("X08_SUPPLIER_ACCOUNT_CHANGED", "HIGH")
    assert (f.facts["earlierAccount"], f.facts["newAccount"]) == ("••••1111", "••••9999")


@pytest.mark.parametrize("code", ["B01_GAMBLING_INDICATORS", "C02_NEGATIVE_BALANCE_DAYS"])
def test_a_check_runs_only_when_the_policy_enables_it(code):
    lines = [line("t1", date(2026, 3, 3), "-50", "SLOT GAMES 88", tags=["GAMBLING"])]
    off = FORENSICS.model_copy(update={"enabled": FORENSICS.enabled - {code}})
    assert code not in codes(
        run_month_checks(replace(ctx(lines=lines, negative_days=9), policy=off))
    )
