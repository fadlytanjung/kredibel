"""Clients and suppliers built by the month run (docs/09 §3.13)."""

from typing import Protocol

from app.domain.counterparties import Counterparty


class CounterpartyRepository(Protocol):
    async def replace_all(self, org_id: str, parties: list[Counterparty]) -> None:
        """The run's full picture: upsert by deterministic ID, drop the ones no longer seen."""
        ...

    async def list_counterparties(
        self,
        org_id: str,
        *,
        role: str | None = None,
        q: str | None = None,
        limit: int = 200,
        cursor: str | None = None,
    ) -> tuple[list[Counterparty], str | None]:
        """By name; `q` matches the name or an alias, case-insensitively."""
        ...

    async def get(self, org_id: str, counterparty_id: str) -> Counterparty | None: ...
