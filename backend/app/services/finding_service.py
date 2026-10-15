"""Finding service (spec 008, AC-008-9).

Handles acknowledge and dismiss findings with audit trail and month re-scoring.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.core.auth import Principal
from app.core.clock import Clock
from app.domain.errors import NotFoundError, ValidationProblem
from app.domain.findings import Finding
from app.ports.document_repository import DocumentRepository
from app.ports.finding_repository import FindingRepository
from app.ports.month_repository import MonthRepository


class FindingUpdateRequest(BaseModel):
    status: Literal["ACKNOWLEDGED", "DISMISSED"]
    reason: str | None = None


class FindingService:
    def __init__(
        self,
        finding_repo: FindingRepository,
        month_repo: MonthRepository,
        doc_repo: DocumentRepository,
        clock: Clock,
    ) -> None:
        self._finding_repo = finding_repo
        self._month_repo = month_repo
        self._doc_repo = doc_repo
        self._clock = clock

    async def get_finding(self, principal: Principal, finding_id: str) -> Finding:
        org_id = principal.org_id
        if not org_id:
            raise NotFoundError("Finding not found")
        finding = await self._finding_repo.get_finding(org_id, finding_id)
        if finding is None:
            raise NotFoundError("Finding not found")
        return finding

    async def update_finding(
        self,
        principal: Principal,
        finding_id: str,
        update: FindingUpdateRequest,
    ) -> Finding:
        org_id = principal.org_id
        if not org_id:
            raise NotFoundError("Finding not found")

        finding = await self._finding_repo.get_finding(org_id, finding_id)
        if finding is None:
            raise NotFoundError("Finding not found")

        if update.status == "DISMISSED":
            if finding.severity in ("CRITICAL", "HIGH") and (
                not update.reason or len(update.reason.strip()) < 10
            ):
                raise ValidationProblem(
                    field="reason",
                    message=(
                        "Dismissing a CRITICAL or HIGH finding requires a reason "
                        "of at least 10 characters."
                    ),
                )
            finding.status = "DISMISSED"
            finding.dismissal = {
                "by": principal.uid,
                "at": self._clock.now().isoformat(),
                "reason": update.reason,
            }
        elif update.status == "ACKNOWLEDGED":
            finding.status = "ACKNOWLEDGED"

        await self._finding_repo.save_finding(org_id, finding)

        months_to_mark: set[str] = set()
        if finding.month:
            months_to_mark.add(finding.month)
        if finding.doc_id:
            doc = await self._doc_repo.get_document(org_id, finding.doc_id)
            if doc:
                months_to_mark.update(doc.months)

        for m_str in months_to_mark:
            m_obj = await self._month_repo.get(org_id, m_str)
            if m_obj:
                m_obj.dirty = True
                await self._month_repo.save(org_id, m_obj)

        return finding
