"""A person's decisions (docs/09 §3.21), written together with their audit event."""

from typing import Protocol

from app.domain.models.decision import Decision
from app.domain.models.events import AuditEvent


class DecisionRepository(Protocol):
    async def save(self, org_id: str, decision: Decision, event: AuditEvent) -> None:
        """Create or update a decision and append its audit event in one write."""
        ...

    async def get(self, org_id: str, decision_id: str) -> Decision | None: ...

    async def list_decisions(
        self,
        org_id: str,
        *,
        kind: str | None = None,
        doc_id: str | None = None,
        record_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[Decision]:
        """Newest first."""
        ...
