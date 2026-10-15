"""Decision routes (docs/10; contracts/openapi.yaml /api/decisions; ADR-025)."""

from datetime import date
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.api.deps import ServiceProvider, org_of
from app.core.auth import Principal
from app.domain.models.decision import Decision


class _Body(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class MoneyIn(_Body):
    amount: Decimal = Field(max_digits=18, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)


class DecisionCreateBody(_Body):
    kind: Literal[
        "DOCUMENT_APPROVAL", "PAYMENT_CONFIRMATION", "CURRENCY_AGREEMENT", "SUPPORT_NOT_REQUIRED"
    ]
    doc_id: str | None = None
    invoice_id: str | None = None
    receipt_id: str | None = None
    tx_id: str | None = None
    amount: MoneyIn | None = None
    paid_on: date | None = None
    method: Literal["CASH", "CARD", "TRANSFER", "CHEQUE", "OTHER"] | None = None
    reason: str | None = Field(default=None, min_length=3, max_length=500)


def decision_body(d: Decision) -> dict[str, Any]:
    return {
        "decisionId": d.decision_id,
        "kind": d.kind,
        "status": d.status,
        "docId": d.doc_id,
        "invoiceId": d.invoice_id,
        "receiptId": d.receipt_id,
        "txId": d.tx_id,
        "amount": None
        if d.amount is None
        else {"amount": f"{d.amount:.2f}", "currency": d.currency},
        "paidOn": d.paid_on.isoformat() if d.paid_on else None,
        "method": d.method,
        "reason": d.reason,
        "printedCurrency": d.printed_currency,
        "months": d.months,
        "decidedBy": d.decided_by,
        "decidedAt": d.decided_at.isoformat(),
        "withdrawnBy": d.withdrawn_by,
        "withdrawnAt": d.withdrawn_at.isoformat() if d.withdrawn_at else None,
    }


def create_decisions_router(provider: ServiceProvider, workspace_dep: Any) -> APIRouter:
    router = APIRouter(prefix="/api/decisions", tags=["months"])

    @router.get("")
    async def list_decisions(
        kind: str | None = Query(default=None),
        doc_id: str | None = Query(default=None, alias="docId"),
        record_id: str | None = Query(default=None, alias="recordId"),
        limit: int = Query(default=200, ge=1, le=500),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        found = await provider.decision_service.list_decisions(
            org_of(principal), kind=kind, doc_id=doc_id, record_id=record_id, limit=limit
        )
        return {"items": [decision_body(d) for d in found]}

    @router.post("", status_code=status.HTTP_201_CREATED)
    async def create_decision(
        body: DecisionCreateBody, principal: Principal = Depends(workspace_dep)
    ) -> dict[str, Any]:
        decision = await provider.decision_service.create(
            principal,
            kind=body.kind,
            doc_id=body.doc_id,
            invoice_id=body.invoice_id,
            receipt_id=body.receipt_id,
            tx_id=body.tx_id,
            amount=body.amount.amount if body.amount else None,
            currency=body.amount.currency if body.amount else None,
            paid_on=body.paid_on,
            method=body.method,
            reason=body.reason,
        )
        return decision_body(decision)

    @router.delete("/{decision_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def withdraw_decision(
        decision_id: str, principal: Principal = Depends(workspace_dep)
    ) -> None:
        await provider.decision_service.withdraw(principal, decision_id)

    return router
