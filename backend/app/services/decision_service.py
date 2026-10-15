"""A person's decisions (ADR-025, docs/10): validated, audited, and the months concerned re-run.

A decision never creates bank cash or a match. Approval, currency agreement and "support not
required" are one per subject (posting again returns the active one); payment confirmations can be
several, for partial payments, in the workspace currency without conversion.
"""

from collections.abc import Sequence
from dataclasses import replace
from datetime import date
from decimal import Decimal

from app.core.auth import Principal
from app.core.clock import Clock
from app.core.ids import content_id, new_id
from app.domain.errors import NotFoundError, ValidationProblem, WorkspaceRequiredError
from app.domain.models.decision import Decision, DecisionKind, PaymentMethodPaid
from app.domain.models.events import AuditEvent
from app.domain.models.invoice import Invoice, Receipt
from app.ports.bank_line_repository import BankLineRepository
from app.ports.decision_repository import DecisionRepository
from app.ports.document_repository import DocumentRepository
from app.ports.month_repository import MonthRepository
from app.ports.record_repository import DocumentRecords
from app.ports.task_queue import TaskQueue
from app.ports.workspace_repository import WorkspaceRepository


class DecisionService:
    def __init__(
        self,
        *,
        decisions: DecisionRepository,
        doc_repo: DocumentRepository,
        invoices: DocumentRecords[Invoice],
        receipts: DocumentRecords[Receipt],
        bank_lines: BankLineRepository,
        workspaces: WorkspaceRepository,
        month_repo: MonthRepository,
        task_queue: TaskQueue,
        clock: Clock,
        month_run_delay_seconds: int,
    ) -> None:
        self._decisions = decisions
        self._docs = doc_repo
        self._invoices = invoices
        self._receipts = receipts
        self._lines = bank_lines
        self._workspaces = workspaces
        self._months = month_repo
        self._queue = task_queue
        self._clock = clock
        self._delay = month_run_delay_seconds

    async def list_decisions(
        self,
        org_id: str,
        *,
        kind: str | None,
        doc_id: str | None,
        record_id: str | None,
        limit: int,
    ) -> list[Decision]:
        return await self._decisions.list_decisions(
            org_id, kind=kind, doc_id=doc_id, record_id=record_id, limit=limit
        )

    async def create(
        self,
        principal: Principal,
        *,
        kind: DecisionKind,
        doc_id: str | None = None,
        invoice_id: str | None = None,
        receipt_id: str | None = None,
        tx_id: str | None = None,
        amount: Decimal | None = None,
        currency: str | None = None,
        paid_on: date | None = None,
        method: PaymentMethodPaid | None = None,
        reason: str | None = None,
    ) -> Decision:
        org_id = _org(principal)
        workspace = await self._workspaces.get_workspace(org_id)
        if workspace is None:
            raise WorkspaceRequiredError()
        base = Decision(
            decision_id="",
            kind=kind,
            decided_by=principal.uid,
            decided_at=self._clock.now(),
            reason=reason.strip() if reason else None,
        )
        if kind == "DOCUMENT_APPROVAL":
            doc = await self._document(org_id, doc_id)
            decision = replace(
                base,
                decision_id=content_id("dec", kind, doc.doc_id),
                doc_id=doc.doc_id,
                months=list(doc.months),
            )
        elif kind == "CURRENCY_AGREEMENT":
            doc = await self._document(org_id, doc_id)
            printed = await self._printed_currency(org_id, doc.doc_id, doc.statement_meta)
            if printed == workspace.currency:
                raise ValidationProblem(
                    "docId", "The document is already in the workspace currency."
                )
            decision = replace(
                base,
                decision_id=content_id("dec", kind, doc.doc_id),
                doc_id=doc.doc_id,
                printed_currency=printed,
                currency=workspace.currency,
                months=list(doc.months),
            )
        elif kind == "SUPPORT_NOT_REQUIRED":
            _require(reason, "reason", "Say why this line needs no supporting document.")
            if not tx_id or (line := await self._lines.get_line(org_id, tx_id)) is None:
                raise NotFoundError("Bank line not found")
            decision = replace(
                base,
                decision_id=content_id("dec", kind, tx_id),
                tx_id=tx_id,
                doc_id=line.doc_id,
                months=[line.month],
            )
        else:
            decision = await self._payment(
                org_id,
                base,
                workspace.currency,
                invoice_id,
                receipt_id,
                amount,
                currency,
                paid_on,
                method,
                reason,
            )
        if decision.kind != "PAYMENT_CONFIRMATION":
            existing = await self._decisions.get(org_id, decision.decision_id)
            if existing is not None and existing.status == "ACTIVE":
                return existing
        await self._decisions.save(
            org_id, decision, self._event(principal, decision, "DECISION_RECORDED")
        )
        await self._rerun(org_id, decision.months)
        return decision

    async def withdraw(self, principal: Principal, decision_id: str) -> None:
        org_id = _org(principal)
        decision = await self._decisions.get(org_id, decision_id)
        if decision is None:
            raise NotFoundError("Decision not found")
        if decision.status == "WITHDRAWN":
            return
        withdrawn = replace(
            decision, status="WITHDRAWN", withdrawn_by=principal.uid, withdrawn_at=self._clock.now()
        )
        await self._decisions.save(
            org_id, withdrawn, self._event(principal, withdrawn, "DECISION_WITHDRAWN")
        )
        await self._rerun(org_id, withdrawn.months)

    async def _payment(
        self,
        org_id: str,
        base: Decision,
        workspace_currency: str,
        invoice_id: str | None,
        receipt_id: str | None,
        amount: Decimal | None,
        currency: str | None,
        paid_on: date | None,
        method: PaymentMethodPaid | None,
        reason: str | None,
    ) -> Decision:
        if bool(invoice_id) == bool(receipt_id):
            raise ValidationProblem(
                "invoiceId", "Confirm the payment of one invoice or one receipt."
            )
        record: Invoice | Receipt | None = (
            await self._invoices.get_record(org_id, invoice_id)
            if invoice_id
            else await self._receipts.get_record(org_id, receipt_id or "")
        )
        if record is None:
            raise NotFoundError("Invoice or receipt not found")
        if amount is None or amount <= 0:
            raise ValidationProblem("amount", "Give the amount that was paid.")
        if currency != workspace_currency:
            raise ValidationProblem(
                "amount",
                f"Give the amount in {workspace_currency}; Kredibel does not convert currencies.",
            )
        if record.total is not None and amount > record.total:
            raise ValidationProblem("amount", "The amount is more than the document's total.")
        if paid_on is None:
            raise ValidationProblem("paidOn", "Give the date of the payment.")
        if method is None:
            raise ValidationProblem("method", "Say how it was paid.")
        _require(reason, "reason", "Say how you know it was paid.")
        months = sorted({m for m in (record.month, f"{paid_on:%Y-%m}") if m})
        return replace(
            base,
            decision_id=new_id("dec"),
            invoice_id=invoice_id,
            receipt_id=receipt_id,
            doc_id=record.doc_id,
            amount=amount.quantize(Decimal("0.01")),
            currency=currency,
            paid_on=paid_on,
            method=method,
            months=months,
        )

    async def _document(self, org_id: str, doc_id: str | None):
        doc = await self._docs.get_document(org_id, doc_id) if doc_id else None
        if doc is None:
            raise NotFoundError("Document not found")
        return doc

    async def _printed_currency(
        self, org_id: str, doc_id: str, statement_meta: dict | None
    ) -> str | None:
        if statement_meta and statement_meta.get("currency"):
            return statement_meta["currency"]
        for store in (self._invoices, self._receipts):
            for record in await store.list_records(org_id, doc_id=doc_id, limit=1):
                return record.currency
        return None

    async def _rerun(self, org_id: str, months: Sequence[str]) -> None:
        for month in months:
            generation, _ = await self._months.bump_generation(org_id, month, dirty=True)
            await self._queue.enqueue_month_task(
                org_id, month, generation, delay_seconds=self._delay
            )

    def _event(self, principal: Principal, decision: Decision, kind: str) -> AuditEvent:
        subject = {
            k: v
            for k, v in (
                ("decisionId", decision.decision_id),
                ("docId", decision.doc_id),
                ("invoiceId", decision.invoice_id),
                ("receiptId", decision.receipt_id),
                ("txId", decision.tx_id),
            )
            if v
        }
        return AuditEvent(
            event_id=new_id("evt"),
            type=kind,  # type: ignore[arg-type]
            actor_uid=principal.uid,
            actor_role=principal.role or "owner",
            at=self._clock.now(),
            subject=subject,
            details={"kind": decision.kind, "months": ",".join(decision.months)},
        )


def _org(principal: Principal) -> str:
    if principal.org_id is None:
        raise WorkspaceRequiredError()
    return principal.org_id


def _require(value: str | None, field: str, message: str) -> None:
    if not value or len(value.strip()) < 3:
        raise ValidationProblem(field, message)
