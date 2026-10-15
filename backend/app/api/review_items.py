"""Review item routes (docs/10 §2.5, §4; contracts/openapi.yaml /api/review-items)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.api.deps import ServiceProvider
from app.core.auth import Principal
from app.domain.review_items import ResolveAction, ReviewItem, ReviewItemKind, ReviewItemStatus
from app.services.review_service import ResolveRequest

_MONTH = r"^\d{4}-(0[1-9]|1[0-2])$"


class ResolvePayload(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    action: ResolveAction
    match_id: str | None = None
    bank_line_ids: list[str] = Field(default_factory=list)
    invoice_ids: list[str] = Field(default_factory=list)
    receipt_ids: list[str] = Field(default_factory=list)
    ledger_entry_ids: list[str] = Field(default_factory=list)
    category: str | None = None
    field: str | None = None
    value: str | None = None
    doc_type: str | None = None
    mapping: dict[str, Any] | None = None
    reason: str | None = None
    note: str | None = None


def review_item_body(it: ReviewItem) -> dict[str, Any]:
    candidates = [
        {
            "matchId": c.match_id,
            "bankLineIds": c.bank_line_ids,
            "invoiceIds": c.invoice_ids,
            "receiptIds": c.receipt_ids,
            "score": str(c.score),
            "reasons": c.reasons,
        }
        for c in it.suggestion.candidates
    ]
    resolution = None
    if it.resolution:
        resolution = {
            "action": it.resolution.action,
            "note": it.resolution.note,
            "resolvedBy": it.resolution.resolved_by,
            "resolvedAt": (
                it.resolution.resolved_at.isoformat() if it.resolution.resolved_at else None
            ),
        }
    return {
        "itemId": it.item_id,
        "kind": it.kind,
        "month": it.month,
        "docId": it.doc_id,
        "status": it.status,
        "priority": it.priority,
        "title": it.title,
        "subject": {
            "bankLineIds": it.subject.bank_line_ids,
            "invoiceIds": it.subject.invoice_ids,
            "receiptIds": it.subject.receipt_ids,
            "ledgerEntryIds": it.subject.ledger_entry_ids,
            "docIds": it.subject.doc_ids,
            "matchId": it.subject.match_id,
            "field": it.subject.field,
        },
        "suggestion": {
            "candidates": candidates,
            "reading": it.suggestion.reading,
            "docType": it.suggestion.doc_type,
            "mapping": it.suggestion.mapping,
            "difference": (
                str(it.suggestion.difference) if it.suggestion.difference is not None else None
            ),
            "evidence": it.suggestion.evidence,
        },
        "allowedActions": it.allowed_actions,
        "resolution": resolution,
    }


def create_review_items_router(provider: ServiceProvider, workspace_dep: Any) -> APIRouter:
    router = APIRouter(prefix="/api/review-items", tags=["review"])

    @router.get("")
    async def list_review_items(
        status: ReviewItemStatus | None = Query(default=None),
        kind: ReviewItemKind | None = Query(default=None),
        month: str | None = Query(default=None, pattern=_MONTH),
        limit: int = Query(default=50, ge=1, le=500),
        cursor: str | None = Query(default=None),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        items, next_cursor, counts_by_kind = await provider.review_service.list_items(
            principal,
            status=status,
            kind=kind,
            month=month,
            limit=limit,
            cursor=cursor,
        )
        return {
            "items": [review_item_body(i) for i in items],
            "nextCursor": next_cursor,
            "countsByKind": counts_by_kind,
        }

    @router.get("/{item_id}")
    async def get_review_item(
        item_id: str = Path(..., pattern=r"^itm_[a-f0-9]{16}$"),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        item = await provider.review_service.get_item(principal, item_id)
        return review_item_body(item)

    @router.post("/{item_id}/resolve")
    async def resolve_review_item(
        payload: ResolvePayload,
        item_id: str = Path(..., pattern=r"^itm_[a-f0-9]{16}$"),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        req = ResolveRequest(
            action=payload.action,
            match_id=payload.match_id,
            bank_line_ids=payload.bank_line_ids,
            invoice_ids=payload.invoice_ids,
            receipt_ids=payload.receipt_ids,
            ledger_entry_ids=payload.ledger_entry_ids,
            category=payload.category,
            field=payload.field,
            value=payload.value,
            doc_type=payload.doc_type,
            mapping=payload.mapping,
            reason=payload.reason,
            note=payload.note,
        )
        resolved = await provider.review_service.resolve(principal, item_id, req)
        return review_item_body(resolved)

    return router
