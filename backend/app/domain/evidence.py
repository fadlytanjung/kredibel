"""Payment evidence and bank support (ADR-025, docs/08 §6). Pure.

Four things stay apart: a document's integrity, its payment evidence, a person's decisions about
it, and a bank line's support. Bank evidence comes only from confirmed matches; a person's payment
confirmation is shown next to it, never added to bank cash and never counted twice when the bank
shows the same payment later. A document whose payment window no statement covers waits for the
statement instead of being called unpaid.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from .reconcile import Allocation
from .reconciliation_policy import ReconciliationPolicy

PaymentEvidence = Literal[
    "CURRENCY_TO_CONFIRM",
    "PAID_BANK",
    "PARTIAL_BANK",
    "PROPOSED",
    "CONFIRMED_BY_YOU",
    "PAID_CASH",
    "WAITING_FOR_STATEMENT",
    "NO_BANK_MATCH",
    "NOT_DUE",
    "UNPAID",
]
Support = Literal["EXCLUDED", "MATCHED", "PROPOSED", "NOT_REQUIRED", "NO_SUPPORT"]
ZERO = Decimal("0")


@dataclass(frozen=True)
class AccountSpan:
    account: str
    start: date
    end: date


@dataclass(frozen=True)
class DocumentFacts:
    record_id: str
    kind: Literal["SALES_INVOICE", "PURCHASE_INVOICE", "RECEIPT"]
    total: Decimal
    issue_date: date
    due_date: date | None
    printed_currency: str | None
    currency_accepted: (
        bool  # a person agreed to use the amounts unchanged in the workspace currency
    )
    payment_method: Literal["CASH", "CARD", "TRANSFER", "UNKNOWN"] = "UNKNOWN"


@dataclass(frozen=True)
class PaymentConfirmation:
    """A person's audited statement that a document was paid, without bank evidence."""

    decision_id: str
    record_id: str
    amount: Decimal
    currency: str
    paid_on: date
    method: str
    reason: str


@dataclass(frozen=True)
class DocumentEvidence:
    record_id: str
    payment: PaymentEvidence
    covered: bool
    bank_paid: Decimal
    confirmed_paid: Decimal
    outstanding: Decimal
    printed_currency: str | None
    effective_currency: str
    match_ids: tuple[str, ...] = ()


def covered(spans: Sequence[AccountSpan], start: date, end: date) -> bool:
    """Every account that has statements covers every day from start to end."""
    accounts = sorted({s.account for s in spans})
    if not accounts or end < start:
        return bool(accounts)
    for account in accounts:
        day = start
        for span in sorted((s for s in spans if s.account == account), key=lambda s: s.start):
            if span.start > day:
                break
            day = max(day, span.end + timedelta(days=1))
        if day <= end:
            return False
    return True


def _bank_paid(
    doc: DocumentFacts, allocations: Sequence[Allocation], bank: dict[str, Decimal]
) -> Decimal:
    paid = ZERO
    for a in allocations:
        if a.status != "CONFIRMED" or doc.record_id not in a.right_ids:
            continue
        if "NET_OF_TAX" in a.reasons or len(a.right_ids) > 1:
            paid += (
                doc.total
            )  # a confirmed adjustment, or this invoice's share of a grouped payment
        else:
            paid += sum((abs(bank.get(tx, ZERO)) for tx in a.left_ids), ZERO)
    return min(paid, doc.total)


def document_evidence(
    doc: DocumentFacts,
    allocations: Sequence[Allocation],
    confirmations: Sequence[PaymentConfirmation],
    spans: Sequence[AccountSpan],
    policy: ReconciliationPolicy,
    *,
    workspace_currency: str,
    as_of: date,
    bank_amounts: dict[str, Decimal],
) -> DocumentEvidence:
    mine = [a for a in allocations if doc.record_id in a.right_ids]
    bank_paid = _bank_paid(doc, mine, bank_amounts)
    confirmed_paid = sum((c.amount for c in confirmations if c.record_id == doc.record_id), ZERO)
    outstanding = max(ZERO, doc.total - (bank_paid if bank_paid > 0 else confirmed_paid))
    windows = policy.windows
    if doc.kind == "RECEIPT":
        end = doc.issue_date + timedelta(days=windows.receipt_days)
    else:
        due = doc.due_date or doc.issue_date + timedelta(days=windows.default_terms_days)
        end = due + timedelta(days=windows.grace_days)
    # Payments before the issue date are rare; requiring statements for them would leave nearly
    # every document waiting, so coverage runs from the issue date to the window end or today.
    is_covered = covered(spans, doc.issue_date, min(end, as_of))
    tolerance = policy.tolerance(doc.total, workspace_currency) or ZERO

    payment: PaymentEvidence
    if doc.printed_currency != workspace_currency and not doc.currency_accepted:
        payment = "CURRENCY_TO_CONFIRM"
    elif bank_paid > 0 and doc.total - bank_paid <= tolerance:
        payment = "PAID_BANK"
    elif bank_paid > 0:
        payment = "PARTIAL_BANK"
    elif any(a.status == "PROPOSED" for a in mine):
        payment = "PROPOSED"
    elif confirmed_paid > 0:
        payment = "CONFIRMED_BY_YOU"
    elif doc.kind == "RECEIPT" and doc.payment_method == "CASH":
        payment = "PAID_CASH"
    elif not is_covered:
        payment = "WAITING_FOR_STATEMENT"
    elif doc.kind == "RECEIPT":
        payment = "NO_BANK_MATCH"
    else:
        due = doc.due_date or doc.issue_date + timedelta(days=windows.default_terms_days)
        payment = "NOT_DUE" if as_of <= due else "UNPAID"
    if payment in ("PAID_BANK", "PAID_CASH"):
        outstanding = ZERO
    return DocumentEvidence(
        record_id=doc.record_id,
        payment=payment,
        covered=is_covered,
        bank_paid=bank_paid,
        confirmed_paid=confirmed_paid,
        outstanding=outstanding.quantize(Decimal("0.01")),
        printed_currency=doc.printed_currency,
        effective_currency=workspace_currency,
        match_ids=tuple(sorted(a.match_id for a in mine)),
    )


def line_support(
    tx_id: str, cashflow_class: str, allocations: Sequence[Allocation], *, not_required: bool
) -> Support:
    """A bank line's support. Every eligible line is bank cash; NO_SUPPORT is informational."""
    if cashflow_class == "NON_CASH":
        return "EXCLUDED"
    mine = [a for a in allocations if tx_id in a.left_ids]
    if any(a.status == "CONFIRMED" for a in mine):
        return "MATCHED"
    if mine:
        return "PROPOSED"
    return "NOT_REQUIRED" if not_required else "NO_SUPPORT"
