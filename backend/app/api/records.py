"""Invoice and receipt routes (docs/10 §2.4; contracts/openapi.yaml /api/invoices, /receipts)."""

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import ServiceProvider, org_of
from app.core.auth import Principal
from app.domain.models.invoice import Invoice, Receipt

_MONTH = r"^\d{4}-(0[1-9]|1[0-2])$"


def _money(value: Decimal | None, currency: str) -> dict[str, str] | None:
    return None if value is None else {"amount": f"{value:.2f}", "currency": currency}


def readings_body(consensus: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        name: {
            "status": c["status"],
            "page": c.get("page"),
            "bbox": c.get("bbox"),
            "raw": c.get("raw", {}),
            "sources": [s for s, v in (c.get("raw") or {}).items() if v is not None],
        }
        for name, c in consensus.items()
    }


def invoice_body(inv: Invoice, workspace_currency: str) -> dict[str, Any]:
    cur = inv.currency or workspace_currency
    return {
        "invoiceId": inv.invoice_id,
        "docId": inv.doc_id,
        "kind": inv.kind,
        "number": inv.number,
        "issuerName": inv.issuer_name,
        "issuerTaxIdMasked": inv.issuer_tax_id,
        "buyerName": inv.buyer_name,
        "buyerTaxIdMasked": inv.buyer_tax_id,
        "issueDate": inv.issue_date.isoformat() if inv.issue_date else None,
        "dueDate": inv.due_date.isoformat() if inv.due_date else None,
        "month": inv.month,
        "subtotal": _money(inv.subtotal, cur),
        "tax": _money(inv.tax, cur),
        "total": _money(inv.total, cur),
        "payToBank": inv.pay_to_bank,
        "payToMasked": inv.pay_to_masked,
        "supplyKind": inv.supply_kind,
        "pages": inv.pages,
        "notes": inv.notes,
        "lines": [
            {
                "description": ln.description,
                "qty": None if ln.quantity is None else str(ln.quantity),
                "unitPrice": _money(ln.unit_price, cur),
                "amount": _money(ln.amount, cur),
            }
            for ln in inv.lines
        ],
        "counterpartyId": None,
        "payment": {"state": "UNPAID", "matchIds": []},
        "readings": readings_body(inv.consensus),
        "heldAsDuplicate": False,
    }


def receipt_body(r: Receipt, workspace_currency: str) -> dict[str, Any]:
    cur = r.currency or workspace_currency
    return {
        "receiptId": r.receipt_id,
        "docId": r.doc_id,
        "merchantName": r.merchant_name,
        "merchantTaxIdMasked": r.merchant_tax_id,
        "number": r.number,
        "date": r.date.isoformat() if r.date else None,
        "time": r.time,
        "month": r.month,
        "total": _money(r.total, cur),
        "tax": _money(r.tax, cur),
        "paymentMethod": r.payment_method,
        "items": [{"description": i.description, "amount": _money(i.amount, cur)} for i in r.items],
        "pages": r.pages,
        "notes": r.notes,
        "payment": {"state": "UNPAID", "matchIds": []},
        "readings": readings_body(r.consensus),
        "heldAsDuplicate": False,
    }


def create_records_router(provider: ServiceProvider, workspace_dep: Any) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["books"])

    @router.get("/invoices")
    async def list_invoices(
        doc_id: str | None = Query(default=None, alias="docId"),
        kind: str | None = Query(default=None, pattern="^(SALES|PURCHASE)$"),
        month: str | None = Query(default=None, pattern=_MONTH),
        limit: int = Query(default=200, ge=1, le=500),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        org_id = org_of(principal)
        service = provider.record_service
        found = await service.list_invoices(
            org_id, doc_id=doc_id, month=month, kind=kind, limit=limit
        )
        currency = await service.currency(org_id)
        return {"items": [invoice_body(i, currency) for i in found], "nextCursor": None}

    @router.get("/receipts")
    async def list_receipts(
        doc_id: str | None = Query(default=None, alias="docId"),
        month: str | None = Query(default=None, pattern=_MONTH),
        limit: int = Query(default=200, ge=1, le=500),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        org_id = org_of(principal)
        service = provider.record_service
        found = await service.list_receipts(org_id, doc_id=doc_id, month=month, limit=limit)
        currency = await service.currency(org_id)
        return {"items": [receipt_body(r, currency) for r in found], "nextCursor": None}

    return router
