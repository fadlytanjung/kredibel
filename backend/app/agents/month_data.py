# What a month run reads, turned into the pure domain's inputs (docs/08 §5–§6, ADR-025).
#
# Eligible inputs only: documents that were read (`DONE`), never held as possible duplicates or
# exact copies; statements and records whose printed currency is the workspace's or that a person
# agreed to use unchanged. A person's decisions (manual matches, rejections, currency agreements,
# payment confirmations, support not required) are inputs, never undone by a run.

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from app.agents.deps import PipelineDeps
from app.domain.checks.month import StatementSpan
from app.domain.evidence import AccountSpan, DocumentEvidence, DocumentFacts, PaymentConfirmation
from app.domain.figures import AccountLines
from app.domain.models.bank_line import BankLine
from app.domain.models.decision import Decision
from app.domain.models.document import DocStatus, DocType, Document, DuplicateKind
from app.domain.models.invoice import Invoice, Receipt
from app.domain.models.match import StoredMatch
from app.domain.reconcile import Allocation, Decisions, ManualMatch
from app.domain.reconcile_scoring import MatchRecord


def month_bounds(month: str) -> tuple[date, date]:
    year, number = map(int, month.split("-"))
    return date(year, number, 1), date(year, number, calendar.monthrange(year, number)[1])


def _shift(month: str, by: int) -> str:
    year, number = map(int, month.split("-"))
    index = year * 12 + number - 1 + by
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


@dataclass
class MonthData:
    month: str
    currency: str
    statements: list[Document]
    spans: list[StatementSpan]
    account_of: dict[str, str]  # statement docId → account
    lines: list[BankLine]  # the month's eligible lines
    all_lines: list[BankLine]  # every eligible line
    invoices: list[Invoice]  # every eligible invoice
    receipts: list[Receipt]
    decisions: list[Decision]
    matches: list[StoredMatch]  # every stored match
    accepted_docs: set[str] = field(default_factory=set)
    not_required: set[str] = field(default_factory=set)

    @property
    def computable(self) -> bool:
        first, last = month_bounds(self.month)
        return any(s.start <= last and s.end >= first for s in self.spans)

    def month_lines_by_account(self) -> list[AccountLines]:
        grouped: dict[str, list[BankLine]] = {}
        for line in self.lines:
            grouped.setdefault(self.account_of.get(line.doc_id, line.doc_id), []).append(line)
        return [AccountLines(account, lines) for account, lines in sorted(grouped.items())]

    def covered_whole_month(self) -> bool:
        first, last = month_bounds(self.month)
        accounts = {s.account for s in self.spans}
        return bool(accounts) and all(
            _covers([s for s in self.spans if s.account == a], first, last) for a in accounts
        )


def _covers(spans: list[StatementSpan], first: date, last: date) -> bool:
    day = first
    for s in sorted(spans, key=lambda s: s.start):
        if s.start > day:
            break
        day = max(day, s.end + timedelta(days=1))
    return day > last


def _minor(value: Any) -> Decimal | None:
    return None if value is None else Decimal(value) / 100


def _eligible(doc: Document) -> bool:
    exact = doc.duplicate is not None and doc.duplicate.kind == DuplicateKind.EXACT
    return doc.status == DocStatus.DONE and not doc.held_as_duplicate and not exact


async def read_month(deps: PipelineDeps, org_id: str, month: str) -> MonthData | None:
    """None when the stores a real run needs are not wired (tests of the workflow skeleton)."""
    stores = (deps.workspaces, deps.bank_lines, deps.invoices, deps.receipts, deps.matches)
    if any(s is None for s in stores) or deps.decisions is None or deps.reconciliation is None:
        return None
    assert deps.workspaces and deps.bank_lines and deps.invoices and deps.receipts and deps.matches
    workspace = await deps.workspaces.get_workspace(org_id)
    if workspace is None:
        return None
    currency = workspace.currency
    docs, _ = await deps.doc_repo.list_documents(org_id, limit=500)
    eligible = {d.doc_id: d for d in docs if _eligible(d)}
    decisions = await deps.decisions.list_decisions(org_id, status="ACTIVE", limit=1000)
    accepted = {d.doc_id for d in decisions if d.kind == "CURRENCY_AGREEMENT" and d.doc_id}

    statements: list[Document] = []
    spans: list[StatementSpan] = []
    account_of: dict[str, str] = {}
    for doc in eligible.values():
        meta = doc.statement_meta or {}
        if doc.doc_type != DocType.BANK_STATEMENT or not meta.get("periodStart"):
            continue
        if meta.get("currency") != currency and doc.doc_id not in accepted:
            continue  # its amounts wait for the person's agreement (ADR-025)
        account = " ".join(x for x in (meta.get("bankName"), meta.get("accountMasked")) if x)
        account_of[doc.doc_id] = account or doc.doc_id
        statements.append(doc)
        spans.append(
            StatementSpan(
                doc.doc_id,
                account_of[doc.doc_id],
                date.fromisoformat(meta["periodStart"]),
                date.fromisoformat(meta["periodEnd"]),
                _minor(meta.get("openingMinor")),
                _minor(meta.get("closingMinor")),
            )
        )
    all_lines: list[BankLine] = []
    for doc in statements:
        all_lines += await deps.bank_lines.list_lines(org_id, doc_id=doc.doc_id, limit=5000)
    invoices = [
        i for i in await deps.invoices.list_records(org_id, limit=2000) if i.doc_id in eligible
    ]
    receipts = [
        r for r in await deps.receipts.list_records(org_id, limit=2000) if r.doc_id in eligible
    ]
    return MonthData(
        month=month,
        currency=currency,
        statements=statements,
        spans=spans,
        account_of=account_of,
        lines=[ln for ln in all_lines if ln.month == month],
        all_lines=all_lines,
        invoices=invoices,
        receipts=receipts,
        decisions=decisions,
        matches=await deps.matches.list_matches(org_id),
        accepted_docs=accepted,
        not_required={d.tx_id for d in decisions if d.kind == "SUPPORT_NOT_REQUIRED" and d.tx_id},
    )


# ---------------------------------------------------------------------------- matching inputs


def _conflict(consensus: dict[str, dict[str, Any]], *fields: str) -> bool:
    return any(consensus.get(f, {}).get("status") == "CONFLICT" for f in fields)


def bank_record(line: BankLine, data: MonthData) -> MatchRecord:
    statement = next((s for s in data.statements if s.doc_id == line.doc_id), None)
    currency = (statement.statement_meta or {}).get("currency") if statement else None
    return MatchRecord(
        record_id=line.tx_id,
        kind="BANK",
        amount=line.amount,
        date=line.date,
        currency=currency,
        party=line.counterparty_name,
        description=" ".join(line.description.split()),
        account_id=data.account_of.get(line.doc_id),
        has_conflict=_conflict(line.consensus, "amount", "date"),
        currency_override_confirmed=line.doc_id in data.accepted_docs,
    )


def document_records(data: MonthData) -> list[MatchRecord]:
    """Invoices and receipts the month's payments may settle: issued this month or the one before
    (payments after a month end), never already settled by another month's confirmed match."""
    owners = {data.month, _shift(data.month, -1)}
    taken = {
        r
        for m in data.matches
        if m.status == "CONFIRMED" and m.month != data.month
        for r in m.document_ids
    }
    out: list[MatchRecord] = []
    for inv in data.invoices:
        if inv.month not in owners or inv.invoice_id in taken:
            continue
        out.append(
            MatchRecord(
                record_id=inv.invoice_id,
                kind="SALES_INVOICE" if inv.kind == "SALES" else "PURCHASE_INVOICE",
                amount=inv.total,
                date=inv.issue_date,
                currency=inv.currency,
                party=inv.buyer_name if inv.kind == "SALES" else inv.issuer_name,
                reference=inv.number,
                due_date=inv.due_date,
                has_conflict=_conflict(inv.consensus, "total", "issueDate"),
                currency_override_confirmed=inv.doc_id in data.accepted_docs,
            )
        )
    for rc in data.receipts:
        if rc.month not in owners or rc.receipt_id in taken:
            continue
        out.append(
            MatchRecord(
                record_id=rc.receipt_id,
                kind="RECEIPT",
                amount=rc.total,
                date=rc.date,
                currency=rc.currency,
                party=rc.merchant_name,
                reference=rc.number,
                payment_method=rc.payment_method,
                has_conflict=_conflict(rc.consensus, "total", "date"),
                currency_override_confirmed=rc.doc_id in data.accepted_docs,
            )
        )
    return out


def person_decisions(data: MonthData) -> Decisions:
    mine = [m for m in data.matches if m.month == data.month]
    return Decisions(
        manual=tuple(
            ManualMatch(tuple(m.bank_line_ids), tuple(m.document_ids))
            for m in mine
            if m.method == "MANUAL" and m.status == "CONFIRMED"
        ),
        rejected=frozenset(m.match_id for m in data.matches if m.status == "REJECTED"),
    )


def stored_allocations(matches: list[StoredMatch]) -> list[Allocation]:
    """Stored confirmed and proposed matches as allocations, for evidence and month checks."""
    return [
        Allocation(
            match_id=m.match_id,
            left_ids=tuple(m.bank_line_ids),
            right_ids=tuple(m.document_ids),
            status="CONFIRMED" if m.status == "CONFIRMED" else "PROPOSED",
            method=m.method,
            score=m.score,
            reasons=tuple(m.reasons),
            amount_difference=m.amount_difference,
            requires_review=m.requires_review,
            alternatives=tuple(m.alternatives),
        )
        for m in matches
        if m.status in ("CONFIRMED", "PROPOSED")
    ]


# This run's allocations plus the confirmed and proposed matches of other months, so the month
# checks see payments made in any month: R01 must not call overdue what an earlier statement shows
# paid or a person is asked about, and D07 must see the first payment of an invoice. Checks count
# only CONFIRMED allocations as payments.
def allocations_for_checks(
    fresh: list[Allocation], matches: list[StoredMatch], month: str
) -> list[Allocation]:
    others = [m for m in matches if m.month != month and m.status in ("CONFIRMED", "PROPOSED")]
    return [*fresh, *stored_allocations(others)]


def document_facts(record: Invoice | Receipt, data: MonthData) -> DocumentFacts | None:
    if isinstance(record, Invoice):
        if record.total is None or record.issue_date is None:
            return None
        return DocumentFacts(
            record_id=record.invoice_id,
            kind="SALES_INVOICE" if record.kind == "SALES" else "PURCHASE_INVOICE",
            total=record.total,
            issue_date=record.issue_date,
            due_date=record.due_date,
            printed_currency=record.currency,
            currency_accepted=record.doc_id in data.accepted_docs,
        )
    if record.total is None or record.date is None:
        return None
    return DocumentFacts(
        record_id=record.receipt_id,
        kind="RECEIPT",
        total=record.total,
        issue_date=record.date,
        due_date=None,
        printed_currency=record.currency,
        currency_accepted=record.doc_id in data.accepted_docs,
        payment_method=record.payment_method,
    )


def confirmations(data: MonthData) -> list[PaymentConfirmation]:
    return [
        PaymentConfirmation(
            decision_id=d.decision_id,
            record_id=d.invoice_id or d.receipt_id or "",
            amount=d.amount or Decimal("0"),
            currency=d.currency or data.currency,
            paid_on=d.paid_on or date.min,
            method=d.method or "OTHER",
            reason=d.reason or "",
        )
        for d in data.decisions
        if d.kind == "PAYMENT_CONFIRMATION"
    ]


def account_spans(data: MonthData) -> list[AccountSpan]:
    return [AccountSpan(s.account, s.start, s.end) for s in data.spans]


def evidence_body(e: DocumentEvidence, approved: bool) -> dict[str, Any]:
    def minor(v: Decimal) -> int:
        return int(v * 100)

    return {
        "payment": e.payment,
        "covered": e.covered,
        "bankPaidMinor": minor(e.bank_paid),
        "confirmedPaidMinor": minor(e.confirmed_paid),
        "outstandingMinor": minor(e.outstanding),
        "printedCurrency": e.printed_currency,
        "approved": approved,
        "matchIds": list(e.match_ids),
    }
