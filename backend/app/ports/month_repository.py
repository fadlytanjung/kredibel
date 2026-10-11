"""Month repository port interface (docs/09 §3.9)."""

from typing import Protocol

from app.domain.models.month import Month


class MonthRepository(Protocol):
    """Port for persisting and managing month states."""

    async def get(self, org_id: str, month: str) -> Month | None:
        """Get month record by org_id and yyyy-mm."""
        ...

    async def save(self, org_id: str, month: Month) -> None:
        """Save or update month record."""
        ...

    async def bump_generation(
        self, org_id: str, month: str, dirty: bool = True
    ) -> tuple[int, Month]:
        """Atomically increment generation and mark dirty in a transaction.

        Returns (generation, Month).
        """
        ...

    async def list(self, org_id: str) -> list[Month]:
        """List all months for a workspace."""
        ...
