"""Payment evidence and bank support (spec 007, T007-06a, AC-007-14…16, AC-007-19; ADR-025).

Bank evidence, a person's payment confirmation and support are separate: a confirmation never adds
bank cash, an unmatched bank line is still bank cash, and a document whose payment window no
statement covers waits instead of being called unpaid."""

from datetime import date
from decimal import Decimal as D
from pathlib import Path
from typing import Literal

from app.adapters.policy_files import load_reconciliation_policy
from app.domain.evidence import (
    AccountSpan,
    DocumentFacts,
    PaymentConfirmation,
    document_evidence,
    line_support,
)
from app.domain.reconcile import Allocation

POLICY = load_reconciliation_policy(Path(__file__).resolve().parents[3] / "contracts" / "policy")
MAR = [
    AccountSpan("A ••••4821", date(2026, 3, 1), date(2026, 3, 31)),
    AccountSpan("A ••••4821", date(2026, 4, 1), date(2026, 4, 30)),
]


def inv(
    total: str = "1000.00",
    issued: date = date(2026, 3, 2),
    due: date | None = date(2026, 3, 16),
    **kw,
) -> DocumentFacts:
    base = dict(
        record_id="i1",
        kind="SALES_INVOICE",
        total=D(total),
        issue_date=issued,
        due_date=due,
        printed_currency="MYR",
        currency_accepted=False,
        payment_method="TRANSFER",
    )
    return DocumentFacts(**{**base, **kw})


def alloc(
    left: tuple[str, ...],
    right: tuple[str, ...],
    status: Literal["CONFIRMED", "PROPOSED"] = "CONFIRMED",
    reasons: tuple[str, ...] = (),
) -> Allocation:
    return Allocation(
        "mat_x",
        left,
        right,
        status,
        "AUTO" if status == "CONFIRMED" else None,
        D("0.9"),
        tuple(reasons),
        D(0),
        False,
    )


def evidence(
    doc=None, allocations=(), confirmations=(), spans=MAR, as_of=date(2026, 4, 30), bank=None
):
    return document_evidence(
        doc or inv(),
        list(allocations),
        list(confirmations),
        spans,
        POLICY,
        workspace_currency="MYR",
        as_of=as_of,
        bank_amounts=bank or {},
    )


def test_a_document_paid_in_full_through_the_bank():
    e = evidence(allocations=[alloc(("b1",), ("i1",))], bank={"b1": D("1000.00")})
    assert (e.payment, e.bank_paid, e.outstanding) == ("PAID_BANK", D("1000.00"), D("0.00"))


def test_a_partial_bank_payment_stays_partial():
    e = evidence(allocations=[alloc(("b1",), ("i1",))], bank={"b1": D("400.00")})
    assert (e.payment, e.bank_paid, e.outstanding) == ("PARTIAL_BANK", D("400.00"), D("600.00"))


def test_grouped_payment_pays_each_invoice_its_own_total():
    doc = inv("600.00")
    e = evidence(doc, [alloc(("b1",), ("i1", "i2"))], bank={"b1": D("1000.00")})
    assert (e.payment, e.bank_paid) == ("PAID_BANK", D("600.00"))


def test_without_statement_coverage_the_document_waits_instead_of_being_unpaid():
    e = evidence(spans=[AccountSpan("A ••••4821", date(2026, 3, 20), date(2026, 3, 31))])
    assert (e.payment, e.covered) == ("WAITING_FOR_STATEMENT", False)
    # Two accounts: the one without statements for the window keeps it waiting.
    other = AccountSpan("B ••••0007", date(2026, 3, 1), date(2026, 3, 10))
    assert evidence(spans=[*MAR, other]).payment == "WAITING_FOR_STATEMENT"


def test_covered_and_unmatched_is_not_due_before_the_due_date_and_unpaid_after():
    assert evidence(as_of=date(2026, 3, 20)).payment == "UNPAID"  # due 16 Mar, covered to 20 Mar
    early = evidence(as_of=date(2026, 3, 10), doc=inv(due=date(2026, 3, 31)))
    assert early.payment == "NOT_DUE"


def test_a_proposed_match_asks_a_person():
    assert evidence(allocations=[alloc(("b1",), ("i1",), "PROPOSED")]).payment == "PROPOSED"


def test_a_persons_payment_confirmation_is_shown_apart_from_bank_evidence():
    confirm = PaymentConfirmation(
        "dec_1", "i1", D("1000.00"), "MYR", date(2026, 3, 20), "CASH", "Paid at the counter"
    )
    e = evidence(confirmations=[confirm])
    assert (e.payment, e.bank_paid, e.confirmed_paid) == ("CONFIRMED_BY_YOU", D("0"), D("1000.00"))
    partial = PaymentConfirmation(
        "dec_2", "i1", D("300.00"), "MYR", date(2026, 3, 20), "CASH", "First half"
    )
    e = evidence(confirmations=[partial])
    assert (e.payment, e.outstanding) == ("CONFIRMED_BY_YOU", D("700.00"))
    # Later bank evidence wins and is not counted twice.
    e = evidence(
        allocations=[alloc(("b1",), ("i1",))], confirmations=[confirm], bank={"b1": D("1000.00")}
    )
    assert (e.payment, e.bank_paid, e.confirmed_paid, e.outstanding) == (
        "PAID_BANK",
        D("1000.00"),
        D("1000.00"),
        D("0.00"),
    )


def test_a_foreign_or_unknown_currency_waits_for_the_persons_agreement():
    assert evidence(inv(printed_currency="IDR")).payment == "CURRENCY_TO_CONFIRM"
    assert evidence(inv(printed_currency=None)).payment == "CURRENCY_TO_CONFIRM"
    agreed = evidence(inv(printed_currency="IDR", currency_accepted=True))
    assert agreed.payment == "UNPAID" and agreed.printed_currency == "IDR"


def test_receipts_paid_in_cash_need_no_bank_line():
    cash = inv(kind="RECEIPT", payment_method="CASH", due=None)
    assert evidence(cash).payment == "PAID_CASH"
    assert evidence(cash).outstanding == D("0.00")
    card = inv(kind="RECEIPT", payment_method="CARD", due=None)
    assert evidence(card).payment == "NO_BANK_MATCH"


def test_bank_line_support_is_separate_from_cash():
    allocations = [alloc(("b1",), ("i1",)), alloc(("b2",), ("i2",), "PROPOSED")]
    assert line_support("b1", "OPERATING", allocations, not_required=False) == "MATCHED"
    assert line_support("b2", "OPERATING", allocations, not_required=False) == "PROPOSED"
    assert line_support("b3", "OPERATING", allocations, not_required=False) == "NO_SUPPORT"
    assert line_support("b3", "OPERATING", allocations, not_required=True) == "NOT_REQUIRED"
    assert line_support("b4", "NON_CASH", allocations, not_required=False) == "EXCLUDED"
