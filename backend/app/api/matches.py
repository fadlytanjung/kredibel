"""Read a workspace's reconciliation allocations (spec 007, contracts/openapi.yaml)."""

from typing import Any

from fastapi import APIRouter, Depends, Query

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

    return router
