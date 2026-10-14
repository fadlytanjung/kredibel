"""Scoped ledger reads and human-confirmed reporting classifications (spec 018)."""

from typing import Protocol

from app.domain.models.events import AuditEvent
from app.domain.profit_loss import Classification, LedgerRow


class LedgerRepository(Protocol):
    async def list_rows(self, org_id: str) -> list[LedgerRow]: ...

    async def classifications(self, org_id: str) -> dict[str, Classification]: ...

    async def confirm(
        self, org_id: str, classification: Classification, event: AuditEvent
    ) -> None: ...
