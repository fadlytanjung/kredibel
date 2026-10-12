"""Finding routes (docs/10 §2.5; contracts/openapi.yaml /api/findings)."""

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import ServiceProvider, org_of
from app.core.auth import Principal
from app.domain.findings import Finding

_MONTH = r"^\d{4}-(0[1-9]|1[0-2])$"
_CAMEL = {"doc_id": "docId", "tx_id": "txId", "invoice_id": "invoiceId", "receipt_id": "receiptId"}


def finding_body(f: Finding) -> dict[str, Any]:
    return {
        "findingId": f.finding_id,
        "code": f.code,
        "category": f.category,
        "scope": f.scope,
        "docId": f.doc_id,
        "month": f.month,
        "severity": f.severity,
        "title": f.title,
        "facts": f.facts,
        "explanation": f.explanation,
        "nextSteps": f.next_steps,
        "evidence": [
            {_CAMEL.get(k, k): v for k, v in asdict(e).items() if v is not None} for e in f.evidence
        ],
        "detectedBy": f.detected_by,
        "corroboratedBy": [],
        "status": f.status,
        "dismissal": f.dismissal,
    }


def create_findings_router(provider: ServiceProvider, workspace_dep: Any) -> APIRouter:
    router = APIRouter(prefix="/api/findings", tags=["risk"])

    @router.get("")
    async def list_findings(
        doc_id: str | None = Query(default=None, alias="docId"),
        month: str | None = Query(default=None, pattern=_MONTH),
        status: str | None = Query(
            default=None, pattern="^(OPEN|ACKNOWLEDGED|DISMISSED|RESOLVED)$"
        ),
        limit: int = Query(default=200, ge=1, le=500),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        found = await provider.findings.list_findings(
            org_of(principal), doc_id=doc_id, month=month, status=status, limit=limit
        )
        return {"items": [finding_body(f) for f in found], "nextCursor": None}

    return router
