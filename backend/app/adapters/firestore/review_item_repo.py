"""ReviewItemRepository on Firestore (docs/09 §3.11, §5)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import cast

from google.cloud.firestore import AsyncClient, FieldFilter

from app.adapters.firestore.models.review_item import (
    ReviewCandidateDoc,
    ReviewItemDoc,
    ReviewResolutionDoc,
    ReviewSubjectDoc,
    ReviewSuggestionDoc,
)
from app.adapters.firestore.models.workspace import EventDoc
from app.adapters.firestore.txn import dump
from app.domain.models.events import AuditEvent
from app.domain.review_items import (
    ResolveAction,
    ReviewCandidate,
    ReviewItem,
    ReviewItemKind,
    ReviewItemResolution,
    ReviewItemStatus,
    ReviewSubject,
    ReviewSuggestion,
    queue_page,
    sync_items,
)
from app.ports.review_item_repository import ReviewItemRepository


def _to_doc(item: ReviewItem) -> ReviewItemDoc:
    candidates = [
        ReviewCandidateDoc(
            match_id=c.match_id,
            bank_line_ids=c.bank_line_ids,
            invoice_ids=c.invoice_ids,
            receipt_ids=c.receipt_ids,
            score=str(c.score),
            reasons=c.reasons,
            ai_rank=c.ai_rank,
            ai_reason=c.ai_reason,
        )
        for c in item.suggestion.candidates
    ]
    resolution = None
    if item.resolution:
        resolution = ReviewResolutionDoc(
            action=item.resolution.action,
            note=item.resolution.note,
            resolved_by=item.resolution.resolved_by,
            resolved_at=item.resolution.resolved_at,
        )
    return ReviewItemDoc(
        item_id=item.item_id,
        kind=item.kind,
        month=item.month,
        doc_id=item.doc_id,
        status=item.status,
        priority=item.priority,
        title=item.title,
        subject=ReviewSubjectDoc(
            bank_line_ids=item.subject.bank_line_ids,
            invoice_ids=item.subject.invoice_ids,
            receipt_ids=item.subject.receipt_ids,
            ledger_entry_ids=item.subject.ledger_entry_ids,
            doc_ids=item.subject.doc_ids,
            match_id=item.subject.match_id,
            field=item.subject.field,
        ),
        suggestion=ReviewSuggestionDoc(
            candidates=candidates,
            reading=item.suggestion.reading,
            doc_type=item.suggestion.doc_type,
            confidence=item.suggestion.confidence,
            mapping=item.suggestion.mapping,
            difference=(
                str(item.suggestion.difference) if item.suggestion.difference is not None else None
            ),
            evidence=item.suggestion.evidence,
            ranked_by=item.suggestion.ranked_by,
        ),
        allowed_actions=[str(a) for a in item.allowed_actions],
        resolution=resolution,
        key=item.key,
    )


def _to_domain(doc: ReviewItemDoc) -> ReviewItem:
    candidates = [
        ReviewCandidate(
            match_id=c.match_id,
            bank_line_ids=c.bank_line_ids,
            invoice_ids=c.invoice_ids,
            receipt_ids=c.receipt_ids,
            score=Decimal(c.score),
            reasons=c.reasons,
            ai_rank=c.ai_rank,
            ai_reason=c.ai_reason,
        )
        for c in doc.suggestion.candidates
    ]
    resolution = None
    if doc.resolution:
        resolution = ReviewItemResolution(
            action=cast(ResolveAction | None, doc.resolution.action),
            note=doc.resolution.note,
            resolved_by=doc.resolution.resolved_by,
            resolved_at=doc.resolution.resolved_at,
        )
    return ReviewItem(
        item_id=doc.item_id,
        kind=cast(ReviewItemKind, doc.kind),
        month=doc.month,
        doc_id=doc.doc_id,
        status=cast(ReviewItemStatus, doc.status),
        priority=doc.priority,
        title=doc.title,
        subject=ReviewSubject(
            bank_line_ids=doc.subject.bank_line_ids,
            invoice_ids=doc.subject.invoice_ids,
            receipt_ids=doc.subject.receipt_ids,
            ledger_entry_ids=doc.subject.ledger_entry_ids,
            doc_ids=doc.subject.doc_ids,
            match_id=doc.subject.match_id,
            field=doc.subject.field,
        ),
        suggestion=ReviewSuggestion(
            candidates=candidates,
            reading=doc.suggestion.reading,
            doc_type=doc.suggestion.doc_type,
            confidence=doc.suggestion.confidence,
            mapping=doc.suggestion.mapping,
            difference=(
                Decimal(doc.suggestion.difference)
                if doc.suggestion.difference is not None
                else None
            ),
            evidence=doc.suggestion.evidence,
            ranked_by=doc.suggestion.ranked_by,
        ),
        allowed_actions=cast(list[ResolveAction], doc.allowed_actions),
        resolution=resolution,
        key=doc.key,
    )


_SCAN = 2000


class FirestoreReviewItemRepo(ReviewItemRepository):
    def __init__(self, db: AsyncClient) -> None:
        self._db = db

    def _col(self, org_id: str):
        return self._db.collection("orgs").document(org_id).collection("reviewItems")

    async def list_review_items(
        self,
        org_id: str,
        *,
        status: str | None = None,
        kind: str | None = None,
        month: str | None = None,
        limit: int = 200,
        cursor: str | None = None,
    ) -> tuple[list[ReviewItem], str | None, dict[str, int]]:
        # An equality filter needs no composite index; a workspace holds tens to hundreds of
        # items, so ordering and the other filters run in memory (domain queue_page).
        query = self._col(org_id)
        if status:
            query = query.where(filter=FieldFilter("status", "==", status))
        rows = [
            _to_domain(ReviewItemDoc.model_validate(snap.to_dict() or {}))
            async for snap in query.limit(_SCAN).stream()
        ]
        return queue_page(rows, kind=kind, month=month, limit=limit, cursor=cursor)

    async def get_review_item(self, org_id: str, item_id: str) -> ReviewItem | None:
        snap = await self._col(org_id).document(item_id).get()
        if not snap.exists:
            return None
        return _to_domain(ReviewItemDoc.model_validate(snap.to_dict() or {}))

    async def resolve(self, org_id: str, item: ReviewItem, event: AuditEvent) -> None:
        batch = self._db.batch()
        batch.set(self._col(org_id).document(item.item_id), dump(_to_doc(item)))
        batch.set(
            self._db.collection("orgs")
            .document(org_id)
            .collection("events")
            .document(event.event_id),
            dump(EventDoc(org_id=org_id, **event.model_dump())),
        )
        await batch.commit()

    async def upsert_review_item(self, org_id: str, item: ReviewItem) -> None:
        await self._col(org_id).document(item.item_id).set(dump(_to_doc(item)))

    async def replace_month_review_items(
        self, org_id: str, month: str, fresh: list[ReviewItem], *, now: datetime
    ) -> list[ReviewItem]:
        col = self._col(org_id)
        existing = [
            _to_domain(ReviewItemDoc.model_validate(snap.to_dict() or {}))
            async for snap in col.where(filter=FieldFilter("month", "==", month)).stream()
        ]
        written = sync_items(existing, fresh, now=now)
        batch = self._db.batch()
        for item in written:
            batch.set(col.document(item.item_id), dump(_to_doc(item)))
        if written:
            await batch.commit()
        return written
