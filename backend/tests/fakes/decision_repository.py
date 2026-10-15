"""In-memory decisions with their audit events, for tests."""

from app.domain.models.decision import Decision
from app.domain.models.events import AuditEvent
from app.ports.decision_repository import DecisionRepository


class FakeDecisionRepository(DecisionRepository):
    def __init__(self) -> None:
        self.decisions: dict[tuple[str, str], Decision] = {}
        self.events: list[AuditEvent] = []

    async def save(self, org_id: str, decision: Decision, event: AuditEvent) -> None:
        self.decisions[(org_id, decision.decision_id)] = decision
        self.events.append(event)

    async def get(self, org_id: str, decision_id: str) -> Decision | None:
        return self.decisions.get((org_id, decision_id))

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
        found = [
            d
            for (o, _), d in self.decisions.items()
            if o == org_id
            and (kind is None or d.kind == kind)
            and (doc_id is None or d.doc_id == doc_id)
            and (record_id is None or d.record_id == record_id)
            and (status is None or d.status == status)
        ]
        return sorted(found, key=lambda d: (d.decided_at, d.decision_id), reverse=True)[:limit]
