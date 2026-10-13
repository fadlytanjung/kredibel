"""Content duplicates (docs/08 §2.2): the same statement period, invoice or receipt uploaded again
in another file. Pure: candidates in, the match out. Only the newer document is ever held."""

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from rapidfuzz import fuzz

from app.domain.checks.policy import Duplicates
from app.domain.findings import Severity


def _fold(text: str | None) -> str:
    return " ".join((text or "").upper().split())


def same_party(a: str | None, b: str | None, min_score: int) -> bool:
    return bool(a and b) and fuzz.token_set_ratio(_fold(a), _fold(b)) >= min_score


@dataclass(frozen=True)
class Match:
    code: Literal[
        "D02_STATEMENT_PERIOD_DUPLICATE",
        "D03_INVOICE_DUPLICATE",
        "D04_INVOICE_NUMBER_REUSED",
        "D05_RECEIPT_DUPLICATE",
    ]
    of_doc_id: str
    severity: Severity
    facts: dict[str, str]
    hold: bool  # D04 keeps both: two different invoices share a number


@dataclass(frozen=True)
class StatementKey:
    doc_id: str
    uploaded_at: datetime
    bank: str | None
    last4: str | None
    start: date
    end: date
    rows: frozenset[tuple[date, Decimal, Decimal | None]]  # (date, amount, balance)


def statement_duplicate(
    new: StatementKey, others: list[StatementKey], policy: Duplicates
) -> Match | None:
    """D02: the same account and periods overlapping by at least a day; adjacent periods are not."""
    for old in sorted(others, key=lambda o: o.uploaded_at):
        if old.doc_id == new.doc_id or old.uploaded_at > new.uploaded_at:
            continue
        if not new.last4 or new.last4 != old.last4 or not same_party(new.bank, old.bank, 90):
            continue
        start, end = max(new.start, old.start), min(new.end, old.end)
        days = (end - start).days + 1
        if days < policy.statement_overlap_min_days:
            continue
        mine = {r for r in new.rows if start <= r[0] <= end}
        theirs = {r for r in old.rows if start <= r[0] <= end}
        identical = mine == theirs
        return Match(
            "D02_STATEMENT_PERIOD_DUPLICATE",
            old.doc_id,
            "MEDIUM" if identical else "HIGH",
            {
                "overlapStart": start.isoformat(),
                "overlapEnd": end.isoformat(),
                "overlapDays": str(days),
                "rowsIdentical": "yes" if identical else "no",
                "rowsOnlyHere": str(len(mine - theirs)),
                "rowsOnlyThere": str(len(theirs - mine)),
            },
            hold=True,
        )
    return None


@dataclass(frozen=True)
class InvoiceKey:
    doc_id: str
    uploaded_at: datetime
    issuer: str | None
    number: str | None
    issue_date: date | None
    total: Decimal | None
    pay_to: str | None = None  # the masked account printed for payment


def _number(text: str | None) -> str:
    return re.sub(r"[\s\-/.]", "", text or "").upper()


def invoice_duplicate(
    new: InvoiceKey, others: list[InvoiceKey], policy: Duplicates
) -> Match | None:
    """D03 the same invoice again (issuer and number, or issuer, date and total), HIGH when the copy
    asks to be paid into another account than the original (T006-11); D04 the same issuer and
    number on a different invoice (another total or date)."""
    for old in sorted(others, key=lambda o: o.uploaded_at):
        if old.doc_id == new.doc_id or old.uploaded_at > new.uploaded_at:
            continue
        if not same_party(new.issuer, old.issuer, policy.invoice_issuer_min_score):
            continue
        same_number = bool(_number(new.number)) and _number(new.number) == _number(old.number)
        same_content = new.issue_date == old.issue_date and new.total == old.total
        facts = {
            "number": new.number or "",
            "issueDate": str(new.issue_date or ""),
            "total": str(new.total or ""),
            "otherIssueDate": str(old.issue_date or ""),
            "otherTotal": str(old.total or ""),
        }
        if same_number and not same_content:
            return Match("D04_INVOICE_NUMBER_REUSED", old.doc_id, "HIGH", facts, hold=False)
        if same_number or (same_content and new.total is not None and new.issue_date is not None):
            # A copy that changes where to pay is how a payment is diverted; X08 cannot see it
            # while the copy is held, so the duplicate says it.
            elsewhere = bool(new.pay_to and old.pay_to) and new.pay_to != old.pay_to
            if elsewhere:
                facts |= {"payTo": new.pay_to or "", "otherPayTo": old.pay_to or ""}
            severity: Severity = "HIGH" if elsewhere else "MEDIUM"
            return Match("D03_INVOICE_DUPLICATE", old.doc_id, severity, facts, hold=True)
    return None


@dataclass(frozen=True)
class ReceiptKey:
    doc_id: str
    uploaded_at: datetime
    merchant: str | None
    day: date | None
    total: Decimal | None
    p_hash: str | None


def phash_distance(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def receipt_duplicate(
    new: ReceiptKey, others: list[ReceiptKey], policy: Duplicates
) -> Match | None:
    """D05: same receipt values, or similar images without contradictory available readings.

    Two till rolls often share a layout despite different purchases. pHash is a fallback for
    incomplete readings; it cannot override different merchants, dates or totals (AC-006-3).
    """
    tol = Decimal(policy.receipt_total_tolerance_minor) / 100
    for old in sorted(others, key=lambda o: o.uploaded_at):
        if old.doc_id == new.doc_id or old.uploaded_at > new.uploaded_at:
            continue
        same_fields = (
            same_party(new.merchant, old.merchant, policy.invoice_issuer_min_score)
            and new.day is not None
            and new.day == old.day
            and new.total is not None
            and old.total is not None
            and abs(new.total - old.total) <= tol
        )
        distance = phash_distance(new.p_hash, old.p_hash) if new.p_hash and old.p_hash else None
        contradictory = (
            (
                bool(new.merchant and old.merchant)
                and not same_party(new.merchant, old.merchant, policy.invoice_issuer_min_score)
            )
            or (new.day is not None and old.day is not None and new.day != old.day)
            or (
                new.total is not None and old.total is not None and abs(new.total - old.total) > tol
            )
        )
        same_image = (
            distance is not None and distance <= policy.p_hash_max_distance and not contradictory
        )
        if same_fields or same_image:
            facts = {
                "merchant": new.merchant or "",
                "date": str(new.day or ""),
                "total": str(new.total or ""),
                "imageDistance": "" if distance is None else str(distance),
            }
            return Match("D05_RECEIPT_DUPLICATE", old.doc_id, "MEDIUM", facts, hold=True)
    return None
