"""Explainable candidate scores (AC-007-5/17/19). No assignment, writes or FX conversion.

Inputs are transient projections of records and audited decisions, not persistence models. The
caller supplies the workspace currency, the parent's printed currency, confirmed account mappings
and any currency override decision. Never infer a user's agreement from extracted text.
"""

import datetime as dt
import re
import unicodedata
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Literal

from rapidfuzz.fuzz import token_set_ratio

from app.domain.reconciliation_policy import ReconciliationPolicy

Kind = Literal[
    "BANK", "SALES_INVOICE", "PURCHASE_INVOICE", "RECEIPT", "LEDGER_CASH", "LEDGER_DOCUMENT"
]
INVOICES = ("SALES_INVOICE", "PURCHASE_INVOICE")
BOOKING_ROLES = {"SALES_INVOICE": "RECEIVABLE", "PURCHASE_INVOICE": "PAYABLE", "RECEIPT": "EXPENSE"}


@dataclass(frozen=True)
class MatchRecord:
    record_id: str
    kind: Kind
    amount: Decimal | None  # signed bank/cash-ledger amount; positive document/booking total
    date: dt.date | None
    currency: str | None  # as printed, preserved even after an override
    party: str | None = None
    description: str = ""
    reference: str | None = None
    due_date: dt.date | None = None
    payment_method: Literal["CASH", "CARD", "TRANSFER", "UNKNOWN"] = "UNKNOWN"
    account_id: str | None = None  # only a confirmed ledger-to-bank account mapping
    booking_role: Literal["RECEIVABLE", "PAYABLE", "EXPENSE"] | None = None
    held: bool = False
    has_conflict: bool = False
    currency_override_confirmed: bool = False
    # The spellings the line's counterparty is known by (spec 014): a terse bank description can
    # still name the invoice's party.
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class CandidateScore:
    left_id: str
    right_id: str
    amount: Decimal
    party: Decimal
    reference: Decimal
    date: Decimal
    score: Decimal
    amount_difference: Decimal  # paid minus target, in the fixed workspace currency
    reasons: tuple[str, ...]
    requires_review: bool  # conflict or possible tax adjustment, regardless of total score


def _fold(text: str) -> str:
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return " ".join(re.findall(r"[^\W_]+", text.upper()))


def _reference_in(reference: str | None, text: str) -> Decimal:
    normalized = _fold(reference or "")
    return Decimal(int(bool(normalized) and f" {normalized} " in f" {_fold(text)} "))


def in_workspace_currency(printed: str | None, workspace_currency: str) -> bool:
    """A document that prints no currency is read in the workspace currency (ADR-025, T007-12);
    only a different printed currency waits for a person's agreement."""
    return not printed or printed == workspace_currency


def _valid(item: MatchRecord, workspace_currency: str) -> bool:
    return (
        not item.held
        and item.date is not None
        and item.amount is not None
        and item.amount.is_finite()
        and item.amount != 0
        and (item.kind in ("BANK", "LEDGER_CASH") or item.amount > 0)
        and (
            in_workspace_currency(item.currency, workspace_currency)
            or item.currency_override_confirmed
        )
    )


def _pair_allowed(left: MatchRecord, right: MatchRecord) -> bool:
    assert left.amount is not None and right.amount is not None
    if left.kind == "BANK":
        if right.kind == "SALES_INVOICE":
            return left.amount > 0
        if right.kind == "PURCHASE_INVOICE":
            return left.amount < 0
        if right.kind == "RECEIPT":
            return left.amount < 0 and right.payment_method in ("CARD", "TRANSFER")
        if right.kind == "LEDGER_CASH":
            return (
                left.amount * right.amount > 0
                and left.account_id is not None
                and left.account_id == right.account_id
            )
        return False
    return (
        right.kind == "LEDGER_DOCUMENT"
        and left.kind in BOOKING_ROLES
        and right.booking_role == BOOKING_ROLES[left.kind]
    )


def _proximity(distance: int, window: int) -> Decimal | None:
    if distance > window:
        return None
    return Decimal(1) if window == 0 else 1 - Decimal(distance) / window


def _date_score(
    left: MatchRecord, right: MatchRecord, policy: ReconciliationPolicy
) -> Decimal | None:
    assert left.date is not None and right.date is not None
    win = policy.windows
    if left.kind == "BANK" and right.kind in INVOICES:
        due = right.due_date or right.date + timedelta(days=win.default_terms_days)
        if due < right.date or (right.date - left.date).days > win.invoice_before_issue_days:
            return None
        return _proximity(max(0, (left.date - due).days), win.grace_days)
    days = win.receipt_days if right.kind == "RECEIPT" else win.ledger_days
    return _proximity(abs((left.date - right.date).days), days)


def score_pair(
    left: MatchRecord, right: MatchRecord, policy: ReconciliationPolicy, *, workspace_currency: str
) -> CandidateScore | None:
    """Score an eligible pair. Unconfirmed currency mismatches never participate in matching."""
    if not (_valid(left, workspace_currency) and _valid(right, workspace_currency)):
        return None
    if not _pair_allowed(left, right):
        return None
    assert left.amount is not None and right.amount is not None
    paid, total = abs(left.amount), abs(right.amount)
    tolerance = policy.tolerance(total, workspace_currency)
    date_score = _date_score(left, right, policy)
    if tolerance is None or date_score is None:
        return None
    adjusted = True  # an adjustment a person confirms: never automatic
    invoice = left.kind == "BANK" and right.kind in INVOICES and paid < total
    fee = policy.fee_allowance.get(workspace_currency)
    if abs(paid - total) <= tolerance:
        amount, reason, adjusted = Decimal(1), "AMOUNT_EXACT", False
    elif (
        invoice
        and right.kind == "SALES_INVOICE"
        and left.amount > 0
        and fee is not None
        and total - paid <= fee
    ):
        # A customer's payment short by a transfer fee the paying bank took (checked first: on
        # money in a fee is far more common than a withholding of the same size).
        amount, reason = policy.net_of_tax_amount_score, "FEE_DEDUCTED"
    elif invoice and total * (1 - policy.max_withholding) <= paid:
        amount, reason = policy.net_of_tax_amount_score, "NET_OF_TAX"
    elif invoice and any(
        abs(paid - total * (1 - rate)) <= tolerance for rate in policy.withholding_rates
    ):
        amount, reason = policy.net_of_tax_amount_score, "WITHHOLDING_RATE"
    else:
        return None
    return _score(left, right, policy, amount, reason, date_score, adjusted)


def _score(
    left: MatchRecord,
    right: MatchRecord,
    policy: ReconciliationPolicy,
    amount: Decimal,
    amount_reason: str,
    date_score: Decimal,
    adjusted: bool,
) -> CandidateScore:
    # For document-to-ledger, the document owns the reference and the ledger describes the booking.
    document, payment = (right, left) if left.kind == "BANK" else (left, right)
    party = _party(document, payment)
    reference = _reference_in(document.reference, payment.description)
    w = policy.weights
    score = w.amount * amount + w.party * party + w.reference * reference + w.date * date_score
    reasons = [amount_reason]
    if party >= policy.reason_thresholds.party:
        reasons.append("PARTY_MATCH")
    if reference:
        reasons.append("REFERENCE_IN_TEXT")
    if date_score >= policy.reason_thresholds.date:
        reasons.append("DATE_NEAR")
    assert left.amount is not None and right.amount is not None
    return CandidateScore(
        left.record_id,
        right.record_id,
        amount,
        party,
        reference,
        date_score,
        score,
        abs(left.amount) - abs(right.amount),
        tuple(reasons),
        left.has_conflict or right.has_conflict or adjusted,
    )


def _party(document: MatchRecord, payment: MatchRecord) -> Decimal:
    """The best of the payment's cleaned party, its printed description and its counterparty's
    known spellings against the document's party (AC-023-5)."""
    document_text = _fold(document.party or "")
    names = [payment.party, payment.description, *payment.aliases]
    texts = [_fold(n) for n in names if n and n.strip()]
    if not document_text or not texts:
        return Decimal(0)
    return max(Decimal(str(token_set_ratio(document_text, t))) / 100 for t in texts)


def part_of(
    payment: MatchRecord, document: MatchRecord, policy: ReconciliationPolicy, currency: str
) -> bool:
    """Can this pair be one part of a group: both valid, the pair allowed, inside its date window
    and the same party (partyMinScoreForSplit)."""
    return (
        _valid(payment, currency)
        and _valid(document, currency)
        and _pair_allowed(payment, document)
        and _date_score(payment, document, policy) is not None
        and _party(document, payment) >= policy.thresholds.party_min_score_for_split
    )


def score_group(
    payments: tuple[MatchRecord, ...],
    documents: tuple[MatchRecord, ...],
    policy: ReconciliationPolicy,
    *,
    workspace_currency: str,
) -> CandidateScore | None:
    """One bank row for several documents (GROUPED, 2 to maxGroupParts, more than maxAutoGroupParts
    never automatic) or several bank rows for one invoice (SPLIT, 2 to maxSplitParts). Every part
    must be eligible with its counterpart, show the same party (partyMinScoreForSplit) and fall in
    its date window; the totals must agree within tolerance.
    Groups get no net-of-tax allowance: an approximate group is not evidence (ADR-025)."""
    if (len(payments) == 1) == (len(documents) == 1):
        return None
    parts = max(len(payments), len(documents))
    grouped = len(payments) == 1
    limits = policy.thresholds
    if parts > (limits.max_group_parts if grouped else limits.max_split_parts):
        return None
    pairs = [(p, d) for p in payments for d in documents]
    if not all(_valid(r, workspace_currency) for r in (*payments, *documents)):
        return None
    if not all(_pair_allowed(p, d) for p, d in pairs):
        return None
    if len({d.kind for d in documents}) != 1:
        return None
    dates = [_date_score(p, d, policy) for p, d in pairs]
    parties = [_party(d, p) for p, d in pairs]
    if any(s is None for s in dates) or min(parties) < policy.thresholds.party_min_score_for_split:
        return None
    paid = sum((abs(p.amount) for p in payments if p.amount is not None), Decimal(0))
    total = sum((abs(d.amount) for d in documents if d.amount is not None), Decimal(0))
    tolerance = policy.tolerance(total, workspace_currency)
    if tolerance is None or abs(paid - total) > tolerance:
        return None
    text = " ".join(p.description for p in payments)
    reference = sum((_reference_in(d.reference, text) for d in documents), Decimal(0)) / len(
        documents
    )
    party = min(parties)
    date_score = min(s for s in dates if s is not None)
    w = policy.weights
    score = w.amount + w.party * party + w.reference * reference + w.date * date_score
    reasons = ["AMOUNT_EXACT"]
    if party >= policy.reason_thresholds.party:
        reasons.append("PARTY_MATCH")
    if reference == 1:
        reasons.append("REFERENCE_IN_TEXT")
    if date_score >= policy.reason_thresholds.date:
        reasons.append("DATE_NEAR")
    reasons.append("SPLIT" if len(payments) > 1 else "GROUPED")
    return CandidateScore(
        "|".join(sorted(p.record_id for p in payments)),
        "|".join(sorted(d.record_id for d in documents)),
        Decimal(1),
        party,
        reference,
        date_score,
        score,
        paid - total,
        tuple(reasons),
        any(r.has_conflict for r in (*payments, *documents))
        or (grouped and parts > limits.max_auto_group_parts),
    )
