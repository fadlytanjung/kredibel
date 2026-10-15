"""Profile suggestions from documents (docs/09 §3.14); their hashes live in orgPrivate only."""

from typing import Protocol

from app.domain.models.events import AuditEvent
from app.domain.profile_suggestions import Suggestion


class SuggestionRepository(Protocol):
    async def upsert_open(self, org_id: str, suggestions: list[Suggestion]) -> None:
        """Write PENDING and CONFLICT suggestions by ID; a decided one is never reopened."""
        ...

    async def list_suggestions(
        self, org_id: str, *, status: str | None = None
    ) -> list[Suggestion]: ...

    async def get(self, org_id: str, suggestion_id: str) -> Suggestion | None: ...

    async def decide(self, org_id: str, suggestion: Suggestion, event: AuditEvent) -> None:
        """Store the decided suggestion with its audit event in one write."""
        ...
