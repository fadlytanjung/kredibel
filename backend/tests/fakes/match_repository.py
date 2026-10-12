"""In-memory matches for tests."""

from app.domain.models.match import StoredMatch
from app.ports.match_repository import MatchRepository


class FakeMatchRepository(MatchRepository):
    def __init__(self) -> None:
        self.matches: dict[tuple[str, str], StoredMatch] = {}

    async def replace_month_matches(
        self, org_id: str, month: str, matches: list[StoredMatch]
    ) -> None:
        for key, m in list(self.matches.items()):
            if key[0] == org_id and m.month == month and not m.by_person:
                del self.matches[key]
        for m in matches:
            existing = self.matches.get((org_id, m.match_id))
            if existing is None or not existing.by_person:
                self.matches[(org_id, m.match_id)] = m

    async def list_matches(
        self, org_id: str, *, month: str | None = None, status: str | None = None, limit: int = 1000
    ) -> list[StoredMatch]:
        found = [
            m
            for (o, _), m in self.matches.items()
            if o == org_id
            and (month is None or m.month == month)
            and (status is None or m.status == status)
        ]
        return sorted(found, key=lambda m: m.match_id)[:limit]

    async def save(self, org_id: str, match: StoredMatch) -> None:
        self.matches[(org_id, match.match_id)] = match
