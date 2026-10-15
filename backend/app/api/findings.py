"""Finding routes (docs/10 §2.5; contracts/openapi.yaml /api/findings)."""

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, Path, Query

from app.api.deps import ServiceProvider, org_of
from app.core.auth import Principal
from app.domain.findings import Finding
from app.services.finding_service import FindingUpdateRequest

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
        severity: str | None = Query(default=None, pattern="^(CRITICAL|HIGH|MEDIUM|LOW|INFO)$"),
        code: str | None = Query(default=None),
        limit: int = Query(default=200, ge=1, le=500),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        found = await provider.findings.list_findings(
            org_of(principal), doc_id=doc_id, month=month, status=status, limit=limit
        )
        if severity:
            found = [f for f in found if f.severity == severity]
        if code:
            found = [f for f in found if f.code == code]
        return {"items": [finding_body(f) for f in found], "nextCursor": None}

    @router.get("/{finding_id}")
    async def get_finding(
        finding_id: str = Path(pattern=r"^fnd_[0-9a-f]{16}$"),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        finding = await provider.finding_service.get_finding(principal, finding_id)
        return finding_body(finding)

    @router.patch("/{finding_id}")
    async def update_finding(
        body: FindingUpdateRequest,
        finding_id: str = Path(pattern=r"^fnd_[0-9a-f]{16}$"),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        updated = await provider.finding_service.update_finding(principal, finding_id, body)
        return finding_body(updated)

    return router
