"""In-memory profile suggestions for tests; secrets kept apart as orgPrivate would."""

from dataclasses import replace

from app.domain.models.events import AuditEvent
from app.domain.profile_suggestions import Suggestion
from app.ports.suggestion_repository import SuggestionRepository

_DECIDED = ("ACCEPTED", "REJECTED")


class FakeSuggestionRepository(SuggestionRepository):
    def __init__(self) -> None:
        self.suggestions: dict[tuple[str, str], Suggestion] = {}
        self.secrets: dict[tuple[str, str], dict[str, str]] = {}
        self.events: list[AuditEvent] = []

    async def upsert_open(self, org_id: str, suggestions: list[Suggestion]) -> None:
        for s in suggestions:
            key = (org_id, s.suggestion_id)
            existing = self.suggestions.get(key)
            if existing is not None and existing.status in _DECIDED:
                continue
            self.suggestions[key] = replace(s, secret={})
            if s.secret:
                self.secrets[key] = dict(s.secret)

    async def list_suggestions(self, org_id: str, *, status: str | None = None) -> list[Suggestion]:
        found = [
            s
            for (o, _), s in self.suggestions.items()
            if o == org_id and (status is None or s.status == status)
        ]
        return sorted(found, key=lambda s: (s.field, s.suggestion_id))

    async def get(self, org_id: str, suggestion_id: str) -> Suggestion | None:
        s = self.suggestions.get((org_id, suggestion_id))
        if s is None:
            return None
        return replace(s, secret=dict(self.secrets.get((org_id, suggestion_id), {})))

    async def decide(self, org_id: str, suggestion: Suggestion, event: AuditEvent) -> None:
        self.suggestions[(org_id, suggestion.suggestion_id)] = replace(suggestion, secret={})
        self.events.append(event)
