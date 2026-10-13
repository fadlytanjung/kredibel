"""Review items (spec 009, docs/08 §7, docs/10 §4): one queue for what a person must decide.

Pure: a month's facts in, its open items out, with deterministic IDs so a re-run never duplicates
an item. `sync_items` merges them with the stored items: a person's resolution is kept, an item
whose cause is gone closes (resolved by `system`) and opens again if the cause comes back.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

ReviewItemKind = Literal[
    "UNMATCHED_BANK_LINE",
    "UNMATCHED_DOCUMENT",
    "PROPOSED_MATCH",
    "POSSIBLE_DUPLICATE",
    "LOW_CONFIDENCE_VALUE",
    "LEDGER_DIFFERENCE",
    "CONFIRM_TYPE",
    "CONFIRM_LEDGER_MAPPING",
]

ReviewItemStatus = Literal["OPEN", "RESOLVED", "DISMISSED"]

ResolveAction = Literal[
    "CONFIRM_MATCH",
    "MATCH",
    "REJECT_MATCH",
    "NO_DOCUMENT_NEEDED",
    "NOT_YET_PAID",
    "IGNORE",
    "CONFIRM_DUPLICATE",
    "NOT_DUPLICATE",
    "CORRECT_VALUE",
    "ACCEPT_AS_READ",
    "EXPLAIN",
    "SET_TYPE",
    "CONFIRM_MAPPING",
]

ALLOWED_ACTIONS_BY_KIND: dict[ReviewItemKind, list[ResolveAction]] = {
    "PROPOSED_MATCH": ["CONFIRM_MATCH", "MATCH", "REJECT_MATCH"],
    "UNMATCHED_BANK_LINE": ["MATCH", "NO_DOCUMENT_NEEDED", "IGNORE"],
    "UNMATCHED_DOCUMENT": ["MATCH", "NOT_YET_PAID", "IGNORE"],
    "POSSIBLE_DUPLICATE": ["CONFIRM_DUPLICATE", "NOT_DUPLICATE"],
    "LOW_CONFIDENCE_VALUE": ["ACCEPT_AS_READ"],  # CORRECT_VALUE with T009-03a
    "LEDGER_DIFFERENCE": ["EXPLAIN", "MATCH", "IGNORE"],
    "CONFIRM_TYPE": ["SET_TYPE"],
    "CONFIRM_LEDGER_MAPPING": ["CONFIRM_MAPPING"],
}

SYSTEM = "system"


def compute_item_id(kind: ReviewItemKind, subject_key: str) -> str:
    """docs/09 §4: itm_ + 16 hex characters of sha1(kind + '|' + subject key)."""
    return "itm_" + hashlib.sha1(f"{kind}|{subject_key}".encode()).hexdigest()[:16]


def calculate_item_priority(kind: ReviewItemKind, month_risk_level: str = "LOW") -> int:
    """AC-009-2: possible duplicates first, then items of HIGH and CRITICAL months."""
    base: dict[ReviewItemKind, int] = {
        "POSSIBLE_DUPLICATE": 100,
        "LEDGER_DIFFERENCE": 75,
        "PROPOSED_MATCH": 70,
        "CONFIRM_TYPE": 60,
        "CONFIRM_LEDGER_MAPPING": 60,
        "UNMATCHED_DOCUMENT": 50,
        "UNMATCHED_BANK_LINE": 50,
        "LOW_CONFIDENCE_VALUE": 40,
    }
    if kind == "POSSIBLE_DUPLICATE":
        return base[kind]
    return base[kind] + {"CRITICAL": 25, "HIGH": 15, "MEDIUM": 5}.get(month_risk_level, 0)


@dataclass
class ReviewSubject:
    bank_line_ids: list[str] = field(default_factory=list)
    invoice_ids: list[str] = field(default_factory=list)
    receipt_ids: list[str] = field(default_factory=list)
    ledger_entry_ids: list[str] = field(default_factory=list)
    doc_ids: list[str] = field(default_factory=list)
    match_id: str | None = None
    field: str | None = None


@dataclass
class ReviewCandidate:
    candidate_id: str
    kind: str
    amount: Decimal
    date: str
    counterparty: str | None = None
    reference: str | None = None
    score: Decimal = Decimal(0)
    reasons: list[str] = field(default_factory=list)


@dataclass
class ReviewSuggestion:
    candidates: list[ReviewCandidate] = field(default_factory=list)
    reading: dict[str, Any] | None = None
    doc_type: str | None = None
    mapping: dict[str, Any] | None = None
    difference: Decimal | None = None
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ReviewItemResolution:
    action: ResolveAction | None  # None: the system closed it because its cause is gone
    resolved_by: str
    resolved_at: datetime
    note: str | None = None


@dataclass
class ReviewItem:
    item_id: str
    kind: ReviewItemKind
    month: str | None
    doc_id: str | None
    status: ReviewItemStatus
    priority: int
    title: str
    subject: ReviewSubject
    suggestion: ReviewSuggestion
    allowed_actions: list[ResolveAction]
    resolution: ReviewItemResolution | None = None
    key: str = ""


# ------------------------------------------------------------------------------ month facts

Check = tuple[str, str]  # (field, consensus status)


@dataclass(frozen=True)
class LineFacts:
    tx_id: str
    doc_id: str
    day: date
    amount: Decimal  # signed: money out is negative
    support: str  # MATCHED, PROPOSED, NOT_REQUIRED, NO_SUPPORT, EXCLUDED (ADR-025)
    held: bool = False
    checks: tuple[Check, ...] = ()  # amount and date
    cited_by: tuple[str, ...] = ()  # codes of open findings that name the line


@dataclass(frozen=True)
class RecordFacts:
    record_id: str
    doc_id: str
    kind: Literal["SALES", "PURCHASE", "RECEIPT"]
    number: str | None
    day: date | None
    total: Decimal | None
    payment: str | None  # the payment evidence of the last month run
    held: bool = False
    checks: tuple[Check, ...] = ()  # total and date


@dataclass(frozen=True)
class ProposalFacts:
    match_id: str
    bank_line_ids: tuple[str, ...]
    invoice_ids: tuple[str, ...]
    receipt_ids: tuple[str, ...]
    amount: Decimal
    day: date | None
    score: Decimal
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class HeldCopy:
    doc_id: str
    code: str  # D02, D03, D05
    of_doc_id: str
    title: str  # the duplicate finding's title


_UNPAID = ("UNPAID", "NO_BANK_MATCH")
_LABEL = {"amount": "amount", "total": "total", "date": "date", "issueDate": "date"}


def _money(amount: Decimal, currency: str) -> str:
    return f"{currency} {abs(amount):,.2f}"


def _day(day: date | None) -> str:
    return f"{day.day} {day:%b %Y}" if day else "an unknown date"


def _unsure(checks: tuple[Check, ...], corroborated: bool) -> list[str]:
    """Fields to check: a conflict always; a single reading unless a bank match agrees with it."""
    return [
        f
        for f, status in checks
        if status == "CONFLICT" or (status == "SINGLE_SOURCE" and not corroborated)
    ]


def _first_upper(text: str) -> str:
    return text[:1].upper() + text[1:]


def _record_name(r: RecordFacts) -> str:
    if r.kind == "RECEIPT":
        return f"the receipt of {_day(r.day)}"
    return f"invoice {r.number}" if r.number else f"the invoice of {_day(r.day)}"


def month_items(
    *,
    month: str,
    currency: str,
    risk_level: str,
    lines: list[LineFacts],
    records: list[RecordFacts],
    proposals: list[ProposalFacts],
    held: list[HeldCopy],
) -> list[ReviewItem]:
    """The month's open items (docs/08 §7). One problem, one item: a held copy's records get no
    item of their own, and a record with an uncertain value gets that item, not an unpaid one."""
    out: list[ReviewItem] = []

    def add(
        kind: ReviewItemKind,
        key: str,
        *,
        doc_id: str | None,
        title: str,
        subject: ReviewSubject,
        suggestion: ReviewSuggestion | None = None,
    ) -> None:
        out.append(
            ReviewItem(
                item_id=compute_item_id(kind, key),
                kind=kind,
                month=month,
                doc_id=doc_id,
                status="OPEN",
                priority=calculate_item_priority(kind, risk_level),
                title=title,
                subject=subject,
                suggestion=suggestion or ReviewSuggestion(),
                allowed_actions=list(ALLOWED_ACTIONS_BY_KIND[kind]),
                key=key,
            )
        )

    for copy in held:
        add(
            "POSSIBLE_DUPLICATE",
            copy.doc_id,
            doc_id=copy.doc_id,
            title=copy.title,
            subject=ReviewSubject(doc_ids=[copy.doc_id, copy.of_doc_id]),
            suggestion=ReviewSuggestion(
                evidence=[
                    {"docId": copy.doc_id, "page": 1, "label": "This document"},
                    {"docId": copy.of_doc_id, "page": 1, "label": "Earlier document"},
                ]
            ),
        )

    proposed_records: set[str] = set()
    for p in proposals:
        proposed_records.update((*p.bank_line_ids, *p.invoice_ids, *p.receipt_ids))
        add(
            "PROPOSED_MATCH",
            p.match_id,
            doc_id=None,
            title=f"Confirm the payment of {_money(p.amount, currency)} on {_day(p.day)}",
            subject=ReviewSubject(
                bank_line_ids=list(p.bank_line_ids),
                invoice_ids=list(p.invoice_ids),
                receipt_ids=list(p.receipt_ids),
                match_id=p.match_id,
            ),
            suggestion=ReviewSuggestion(
                candidates=[
                    ReviewCandidate(
                        candidate_id=p.match_id,
                        kind="MATCH",
                        amount=p.amount,
                        date=p.day.isoformat() if p.day else "",
                        score=p.score,
                        reasons=list(p.reasons),
                    )
                ]
            ),
        )

    for r in records:
        if r.held:
            continue
        unsure = _unsure(r.checks, corroborated=r.payment == "PAID_BANK")
        if unsure:
            labels = sorted({_LABEL.get(f, f) for f in unsure})
            add(
                "LOW_CONFIDENCE_VALUE",
                r.record_id,
                doc_id=r.doc_id,
                title=f"Check the {' and '.join(labels)} read from {_record_name(r)}",
                subject=ReviewSubject(
                    invoice_ids=[r.record_id] if r.kind != "RECEIPT" else [],
                    receipt_ids=[r.record_id] if r.kind == "RECEIPT" else [],
                    doc_ids=[r.doc_id],
                    field=unsure[0],
                ),
            )
        elif r.payment in _UNPAID and r.record_id not in proposed_records:
            amount = f" of {_money(r.total, currency)}" if r.total is not None else ""
            title = (
                f"The receipt of {_day(r.day)}{amount} has no bank payment"
                if r.kind == "RECEIPT"
                else f"{_first_upper(_record_name(r))}{amount} is unpaid after its due date"
            )
            add(
                "UNMATCHED_DOCUMENT",
                r.record_id,
                doc_id=r.doc_id,
                title=title,
                subject=ReviewSubject(
                    invoice_ids=[r.record_id] if r.kind != "RECEIPT" else [],
                    receipt_ids=[r.record_id] if r.kind == "RECEIPT" else [],
                    doc_ids=[r.doc_id],
                ),
            )

    for ln in lines:
        if ln.held or ln.tx_id in proposed_records:
            continue
        side = "received" if ln.amount > 0 else "paid out"
        unsure = _unsure(ln.checks, corroborated=ln.support == "MATCHED")
        if unsure:
            labels = sorted({_LABEL.get(f, f) for f in unsure})
            add(
                "LOW_CONFIDENCE_VALUE",
                ln.tx_id,
                doc_id=ln.doc_id,
                title=f"Check the {' and '.join(labels)} of the bank line of {_day(ln.day)}",
                subject=ReviewSubject(
                    bank_line_ids=[ln.tx_id], doc_ids=[ln.doc_id], field=unsure[0]
                ),
            )
        elif ln.support == "NO_SUPPORT" and ln.cited_by:
            add(
                "UNMATCHED_BANK_LINE",
                ln.tx_id,
                doc_id=ln.doc_id,
                title=(
                    f"{_money(ln.amount, currency)} {side} on {_day(ln.day)} "
                    "has no supporting document"
                ),
                subject=ReviewSubject(bank_line_ids=[ln.tx_id], doc_ids=[ln.doc_id]),
                suggestion=ReviewSuggestion(
                    evidence=[{"code": code, "txId": ln.tx_id} for code in ln.cited_by]
                ),
            )
    return out


def sync_items(
    existing: list[ReviewItem], fresh: list[ReviewItem], *, now: datetime
) -> list[ReviewItem]:
    """Items to store for a month (AC-009-1): fresh items open (again); a person's resolution is
    kept; an open item that is no longer fresh closes, resolved by the system. Unchanged closed
    items are not returned."""
    current = {i.item_id: i for i in fresh}
    out: list[ReviewItem] = []
    for old in existing:
        decided = old.status == "DISMISSED" or (
            old.resolution is not None and old.resolution.resolved_by != SYSTEM
        )
        if decided or (old.status != "OPEN" and old.item_id not in current):
            current.pop(old.item_id, None)
            continue
        if old.item_id not in current:
            out.append(
                replace(
                    old,
                    status="RESOLVED",
                    resolution=ReviewItemResolution(
                        action=None, resolved_by=SYSTEM, resolved_at=now, note="Its cause is gone"
                    ),
                )
            )
    out.extend(current.values())
    return out


def queue_page(
    items: list[ReviewItem],
    *,
    kind: str | None,
    month: str | None,
    limit: int,
    cursor: str | None,
) -> tuple[list[ReviewItem], str | None, dict[str, int]]:
    """AC-009-2: highest priority first, then the latest month; counts per kind are taken before
    the kind filter, so every kind's chip keeps its count. The cursor is an offset."""
    rows = [i for i in items if month is None or i.month == month]
    rows.sort(key=lambda i: i.item_id)
    rows.sort(key=lambda i: i.month or "", reverse=True)
    rows.sort(key=lambda i: -i.priority)  # stable: priority, then the latest month, then the ID
    counts: dict[str, int] = {}
    for i in rows:
        counts[i.kind] = counts.get(i.kind, 0) + 1
    rows = [i for i in rows if kind is None or i.kind == kind]
    start = int(cursor) if cursor and cursor.isdigit() else 0
    end = start + limit
    return rows[start:end], (str(end) if end < len(rows) else None), counts
