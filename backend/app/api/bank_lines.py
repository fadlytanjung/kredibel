"""Bank line routes (docs/10 §2.4, contracts/openapi.yaml /api/bank-lines)."""

from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from app.api.deps import ServiceProvider, org_of
from app.api.insights import PERIOD
from app.core.auth import Principal
from app.domain.models.bank_line import BankLine


class BankLineUpdateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str


def _money(value: Decimal | None, currency: str) -> dict[str, str] | None:
    return None if value is None else {"amount": f"{value:.2f}", "currency": currency}


def bank_line_body(line: BankLine, currency: str) -> dict[str, Any]:
    return {
        "txId": line.tx_id,
        "docId": line.doc_id,
        "accountId": None,
        "page": line.page,
        "rowIndex": line.row_index,
        "date": line.date.isoformat(),
        "month": line.month,
        "description": line.description,
        "counterpartyId": None,
        "counterpartyName": line.counterparty_name,
        "amount": _money(line.amount, currency),
        "balance": _money(line.balance, currency),
        "readings": {
            name: {
                "status": c["status"],
                "page": c.get("page"),
                "bbox": c.get("bbox"),
                "raw": c.get("raw", {}),
                "sources": [s for s, v in (c.get("raw") or {}).items() if v is not None],
            }
            for name, c in line.consensus.items()
        },
        "category": line.category,
        "cashflowClass": line.cashflow_class,
        "riskTags": line.risk_tags,
        "categorizedBy": line.categorized_by,
        "source": line.source,
        "notes": line.notes,
        "match": {"state": line.match_state, "matchIds": line.match_ids},
        "support": line.support,
        "heldAsDuplicate": False,
        "corrected": False,
    }


def create_bank_lines_router(provider: ServiceProvider, workspace_dep: Any) -> APIRouter:
    router = APIRouter(prefix="/api/bank-lines", tags=["books"])

    @router.patch("/{tx_id}")
    async def update_bank_line(
        tx_id: str,
        body: BankLineUpdateBody,
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        line, currency = await provider.bank_line_service.set_category(
            principal, tx_id, body.category
        )
        return bank_line_body(line, currency)

    @router.get("")
    async def list_bank_lines(
        doc_id: str | None = Query(default=None, alias="docId"),
        month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
        flow: str | None = Query(default=None, max_length=300),
        period: str = Query(default="all", pattern=PERIOD),
        view: Literal["STATEMENT", "COUNTERPARTIES"] = Query(default="STATEMENT"),
        framework: Literal["IFRS", "US_GAAP"] | None = Query(default=None),
        show_transfers: bool = Query(default=False, alias="showTransfers"),
        limit: int = Query(default=500, ge=1, le=1000),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        if flow:
            # A Sankey band: the flow is rebuilt as the chart asked for it (docs/08 §5.1).
            lines, currency = await provider.insight_service.flow_lines(
                org_of(principal),
                flow,
                period=period,
                view=view,
                framework=framework,
                show_transfers=show_transfers,
            )
            lines = lines[:limit]
        else:
            lines, currency = await provider.bank_line_service.list_lines(
                org_of(principal), doc_id=doc_id, month=month, limit=limit
            )
        total = sum((line.amount for line in lines), Decimal("0"))
        return {
            "items": [bank_line_body(line, currency) for line in lines],
            "nextCursor": None,
            "total": _money(total, currency),
        }

    return router
