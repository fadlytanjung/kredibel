"""The Transactions table (spec 024, AC-024-6; contracts/openapi.yaml /api/transactions)."""

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import ServiceProvider, org_of
from app.core.auth import Principal
from app.domain.transactions import TransactionRow


def transaction_body(row: TransactionRow, currency: str) -> dict[str, Any]:
    line = row.line
    return {
        "txId": line.tx_id,
        "docId": line.doc_id,
        "page": line.page,
        "date": line.date.isoformat(),
        "month": line.month,
        "description": line.description,
        "counterpartyName": line.counterparty_name,
        "amount": {"amount": f"{line.amount:.2f}", "currency": currency},
        "category": line.category,
        "categoryLabel": row.category_label,
        "categorizedBy": line.categorized_by,
        "categoryConfidence": None if row.confidence is None else f"{row.confidence:.2f}",
        "cashflow": {"ifrs": row.ifrs, "usGaap": row.us_gaap},
        "pnlLine": row.pnl_line,
        "subledger": row.subledger,
        "reading": row.reading,
        "match": {
            "state": line.match_state,
            "kind": row.match_kind,
            "records": [
                {"kind": r.kind, "id": r.record_id, "docId": r.doc_id, "label": r.label}
                for r in row.linked
            ],
        },
    }


def create_transactions_router(provider: ServiceProvider, workspace_dep: Any) -> APIRouter:
    router = APIRouter(prefix="/api/transactions", tags=["books"])

    @router.get("")
    async def list_transactions(
        month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        currency, rows = await provider.transaction_service.month(org_of(principal), month)
        return {"month": month, "items": [transaction_body(r, currency) for r in rows]}

    return router
