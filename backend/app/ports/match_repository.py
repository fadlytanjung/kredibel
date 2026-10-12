"""Matches (docs/09 §3.10). A month run replaces only its own AUTO and PROPOSED matches; a person's
MANUAL and REJECTED ones are inputs and are never overwritten by a run."""

from typing import Protocol

from app.domain.models.match import StoredMatch


class MatchRepository(Protocol):
    async def replace_month_matches(
        self, org_id: str, month: str, matches: list[StoredMatch]
    ) -> None:
        """Write the run's matches for the month and drop its stale ones (not a person's)."""
        ...

    async def list_matches(
        self, org_id: str, *, month: str | None = None, status: str | None = None, limit: int = 1000
    ) -> list[StoredMatch]: ...

    async def save(self, org_id: str, match: StoredMatch) -> None:
        """A person's MANUAL match or REJECTED proposal."""
        ...
