"""Clients and suppliers (docs/10 §2.7; spec 014, AC-014-2)."""

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import ServiceProvider, org_of
from app.core.auth import Principal
from app.domain.counterparties import Counterparty


def money(value: Decimal, currency: str) -> dict[str, str]:
    return {"amount": f"{value:.2f}", "currency": currency}


def counterparty_body(c: Counterparty, currency: str) -> dict[str, Any]:
    return {
        "counterpartyId": c.counterparty_id,
        "name": c.name,
        "aliases": list(c.aliases),
        "kind": c.kind,
        "roles": list(c.roles),
        "totalIn": money(c.total_in, currency),
        "totalOut": money(c.total_out, currency),
        "totalsByMonth": {
            month: {
                "in": money(t.in_amount, currency),
                "out": money(t.out_amount, currency),
                "count": t.count,
            }
            for month, t in c.totals_by_month.items()
        },
        "accountsSeen": [
            {
                "accountMasked": a.account_masked,
                "firstSeen": a.first_seen.isoformat(),
                "lastSeen": a.last_seen.isoformat(),
            }
            for a in c.accounts_seen
        ],
        "openInvoices": c.open_invoices,
        "firstDate": c.first_date.isoformat() if c.first_date else None,
        "lastDate": c.last_date.isoformat() if c.last_date else None,
        "sampleEvidence": list(c.sample_evidence),
        "bucket": c.bucket,
    }


def create_counterparties_router(provider: ServiceProvider, workspace_dep: Any) -> APIRouter:
    router = APIRouter(prefix="/api/counterparties", tags=["insight"])

    @router.get("")
    async def list_counterparties(
        role: str | None = Query(
            default=None,
            pattern="^(CLIENT|SUPPLIER|LENDER|OWNER|OWN_ACCOUNT|RELATED_PARTY|GOVERNMENT|OTHER)$",
        ),
        q: str | None = Query(default=None, max_length=100),
        limit: int = Query(default=50, ge=1, le=500),
        cursor: str | None = Query(default=None),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        org_id = org_of(principal)
        service = provider.counterparty_service
        found, next_cursor = await service.list_counterparties(
            org_id, role=role, q=q, limit=limit, cursor=cursor
        )
        currency = await service.currency(org_id)
        return {"items": [counterparty_body(c, currency) for c in found], "nextCursor": next_cursor}

    @router.get("/{counterparty_id}")
    async def get_counterparty(
        counterparty_id: str, principal: Principal = Depends(workspace_dep)
    ) -> dict[str, Any]:
        org_id = org_of(principal)
        service = provider.counterparty_service
        found = await service.get(org_id, counterparty_id)
        return counterparty_body(found, await service.currency(org_id))

    return router
