"""Read a workspace's reconciliation allocations (spec 007, contracts/openapi.yaml)."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.api.deps import ServiceProvider, org_of
from app.core.auth import Principal
from app.domain.models.match import StoredMatch


def match_body(match: StoredMatch, currency: str) -> dict[str, Any]:
    body = {
        "matchId": match.match_id,
        "month": match.month,
        "kind": match.kind,
        "bankLineIds": match.bank_line_ids,
        "invoiceIds": match.invoice_ids,
        "receiptIds": match.receipt_ids,
        "ledgerEntryIds": [],
        "amount": {"amount": f"{match.amount:.2f}", "currency": currency},
        "amountDifference": {"amount": f"{match.amount_difference:.2f}", "currency": currency},
        "method": match.method,
        "status": match.status,
        "score": str(match.score),
        "reasons": match.reasons,
        "alternatives": match.alternatives,
        "requiresReview": match.requires_review,
        "createdBy": match.created_by,
    }
    if match.created_at:
        body["createdAt"] = match.created_at.isoformat()
    return body


class MatchCreateBody(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    bank_line_ids: list[str] = Field(default_factory=list, max_length=3)
    invoice_ids: list[str] = Field(default_factory=list, max_length=5)
    receipt_ids: list[str] = Field(default_factory=list, max_length=5)
    ledger_entry_ids: list[str] = Field(default_factory=list, max_length=5)
    note: str | None = Field(default=None, max_length=500)


def create_matches_router(provider: ServiceProvider, workspace_dep: Any) -> APIRouter:
    router = APIRouter(prefix="/api/matches", tags=["months"])

    @router.get("")
    async def list_matches(
        month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
        status: str | None = Query(default=None, pattern="^(CONFIRMED|PROPOSED|REJECTED)$"),
        kind: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=500),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        org_id = org_of(principal)
        # One indexed filter; apply display filters before the response limit.
        matches = await provider.matches.list_matches(org_id, month=month)
        selected = [
            m
            for m in matches
            if (status is None or m.status == status) and (kind is None or m.kind == kind)
        ]
        currency = await provider.record_service.currency(org_id)
        return {"items": [match_body(m, currency) for m in selected[:limit]], "nextCursor": None}

    @router.post("", status_code=201)
    async def create_match(
        payload: MatchCreateBody,
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        match = await provider.match_service.create_manual_match(
            principal,
            bank_line_ids=payload.bank_line_ids,
            invoice_ids=payload.invoice_ids,
            receipt_ids=payload.receipt_ids,
            ledger_entry_ids=payload.ledger_entry_ids,
            note=payload.note,
        )
        currency = await provider.record_service.currency(org_of(principal))
        return match_body(match, currency)

    @router.delete("/{match_id}", status_code=204)
    async def unmatch(
        match_id: str,
        principal: Principal = Depends(workspace_dep),
    ) -> None:
        await provider.match_service.unmatch(principal, match_id)

    return router

