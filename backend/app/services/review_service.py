"""The review queue (spec 009, docs/10 §2.5, §4): list items and resolve them.

Each action is stored where the month run reads it, through the service that owns that decision:
matches through MatchService, "no document needed" through DecisionService, a duplicate decision on
the document and its records. Every resolution is audited and re-runs the item's month; a person's
resolution is never reopened by a run (domain `sync_items`).
"""

from __future__ import annotations

import dataclasses
from dataclasses import replace
from typing import Any

from app.core.auth import Principal
from app.core.clock import Clock
from app.core.ids import new_id
from app.domain.errors import (
    ActionNotAllowedError,
    ItemAlreadyResolvedError,
    MatchAmountMismatchError,
    NotFoundError,
    ReasonRequiredError,
    ToleranceExceededError,
    WorkspaceRequiredError,
)
from app.domain.models.document import DuplicateDecision
from app.domain.models.events import AuditEvent
from app.domain.models.invoice import Invoice, Receipt
from app.domain.review_items import ResolveAction, ReviewItem, ReviewItemResolution
from app.ports.bank_line_repository import BankLineRepository
from app.ports.document_repository import DocumentRepository
from app.ports.record_repository import DocumentRecords
from app.ports.review_item_repository import ReviewItemRepository
from app.services.bank_line_service import BankLineService
from app.services.decision_service import DecisionService
from app.services.match_service import MatchService
from app.services.month_service import MonthService


def _org(principal: Principal) -> str:
    if principal.org_id is None:
        raise WorkspaceRequiredError()
    return principal.org_id


@dataclasses.dataclass
class ResolveRequest:
    action: ResolveAction
    match_id: str | None = None
    bank_line_ids: list[str] = dataclasses.field(default_factory=list)
    invoice_ids: list[str] = dataclasses.field(default_factory=list)
    receipt_ids: list[str] = dataclasses.field(default_factory=list)
    ledger_entry_ids: list[str] = dataclasses.field(default_factory=list)
    category: str | None = None
    field: str | None = None
    value: str | None = None
    doc_type: str | None = None
    mapping: dict[str, Any] | None = None
    reason: str | None = None
    note: str | None = None


class ReviewService:
    def __init__(
        self,
        *,
        review_items: ReviewItemRepository,
        matches: MatchService,
        decisions: DecisionService,
        bank_line_service: BankLineService,
        months: MonthService,
        doc_repo: DocumentRepository,
        bank_lines: BankLineRepository,
        invoices: DocumentRecords[Invoice],
        receipts: DocumentRecords[Receipt],
        clock: Clock,
    ) -> None:
        self._items = review_items
        self._matches = matches
        self._decisions = decisions
        self._line_service = bank_line_service
        self._months = months
        self._docs = doc_repo
        self._holders = (bank_lines, invoices, receipts)
        self._clock = clock

    async def list_items(
        self,
        principal: Principal,
        *,
        status: str | None = None,
        kind: str | None = None,
        month: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[ReviewItem], str | None, dict[str, int]]:
        return await self._items.list_review_items(
            _org(principal), status=status, kind=kind, month=month, limit=limit, cursor=cursor
        )

    async def get_item(self, principal: Principal, item_id: str) -> ReviewItem:
        item = await self._items.get_review_item(_org(principal), item_id)
        if item is None:
            raise NotFoundError(f"Review item {item_id} not found")
        return item

    async def resolve(
        self, principal: Principal, item_id: str, request: ResolveRequest
    ) -> ReviewItem:
        org_id = _org(principal)
        item = await self.get_item(principal, item_id)
        if item.status != "OPEN":
            raise ItemAlreadyResolvedError(item_id)
        if request.action not in item.allowed_actions:
            raise ActionNotAllowedError(request.action, item.kind, list(item.allowed_actions))
        note = (request.reason or request.note or "").strip() or None
        if request.action == "IGNORE" and note is None:
            raise ReasonRequiredError("Say why this item can be ignored.")

        # The decision itself, where the month run reads it. Each of these re-runs the month.
        rerun = True
        match request.action:
            case "CONFIRM_MATCH":
                await self._matches.confirm(
                    principal, request.match_id or item.subject.match_id or ""
                )
            case "REJECT_MATCH":
                await self._matches.unmatch(
                    principal, request.match_id or item.subject.match_id or ""
                )
            case "MATCH":
                await self._match(principal, item, request, note)
            case "NO_DOCUMENT_NEEDED":
                tx_id = (request.bank_line_ids or item.subject.bank_line_ids or [""])[0]
                if request.category:
                    await self._line_service.set_category(principal, tx_id, request.category)
                await self._decisions.create(
                    principal,
                    kind="SUPPORT_NOT_REQUIRED",
                    tx_id=tx_id,
                    reason=note or "No supporting document is needed for this line.",
                )
            case "CONFIRM_DUPLICATE" | "NOT_DUPLICATE":
                await self._decide_duplicate(principal, item, request.action == "CONFIRM_DUPLICATE")
            case _:
                rerun = False  # NOT_YET_PAID, IGNORE, ACCEPT_AS_READ: the item is the decision

        now = self._clock.now()
        resolved = replace(
            item,
            status="RESOLVED",
            resolution=ReviewItemResolution(
                action=request.action, resolved_by=principal.uid, resolved_at=now, note=note
            ),
        )
        event = AuditEvent(
            event_id=new_id("evt"),
            type="REVIEW_ITEM_RESOLVED",
            actor_uid=principal.uid,
            actor_role=principal.role or "owner",
            at=now,
            subject={"itemId": item_id, "month": item.month or ""},
            details={
                "kind": item.kind,
                "action": request.action,
                **({"note": note} if note else {}),
            },
        )
        await self._items.resolve(org_id, resolved, event)
        if not rerun and item.month:
            await self._months.mark_dirty(org_id, [item.month], reason="review_item_resolved")
        return resolved

    async def _match(
        self, principal: Principal, item: ReviewItem, request: ResolveRequest, note: str | None
    ) -> None:
        """A manual match: the request's records, or the item's own on the side it leaves out."""
        chose_documents = request.invoice_ids or request.receipt_ids or request.ledger_entry_ids
        subject = item.subject
        try:
            await self._matches.create_manual_match(
                principal,
                bank_line_ids=request.bank_line_ids or subject.bank_line_ids,
                invoice_ids=request.invoice_ids if chose_documents else subject.invoice_ids,
                receipt_ids=request.receipt_ids if chose_documents else subject.receipt_ids,
                ledger_entry_ids=(
                    request.ledger_entry_ids if chose_documents else subject.ledger_entry_ids
                ),
                note=note,
            )
        except ToleranceExceededError as error:
            difference = error.extras.get("difference")
            raise MatchAmountMismatchError(error.detail, difference=difference) from error

    async def _decide_duplicate(self, principal: Principal, item: ReviewItem, copy: bool) -> None:
        """AC-006-6: "duplicate" keeps the copy's values out; "not a duplicate" releases them."""
        org_id = _org(principal)
        doc = await self._docs.get_document(org_id, item.doc_id or "")
        if doc is None or doc.duplicate is None:
            raise NotFoundError("The held document is gone")
        now = self._clock.now()
        decided = replace(
            doc,
            duplicate=replace(
                doc.duplicate,
                decision=DuplicateDecision.CONFIRMED if copy else DuplicateDecision.REJECTED,
                review_item_id=item.item_id,
                decided_by=principal.uid,
                decided_at=now,
            ),
            held_as_duplicate=copy,
        )
        event = AuditEvent(
            event_id=new_id("evt"),
            type="DUPLICATE_CONFIRMED" if copy else "DUPLICATE_REJECTED",
            actor_uid=principal.uid,
            actor_role=principal.role or "owner",
            at=now,
            subject={"docId": doc.doc_id, "ofDocId": doc.duplicate.of_doc_id},
            details={"code": doc.duplicate.code},
        )
        await self._docs.save_document(org_id, decided, event)
        if not copy:
            for holder in self._holders:
                await holder.set_held(org_id, doc.doc_id, False)
        await self._months.mark_dirty(org_id, list(doc.months), reason="duplicate_decided")
