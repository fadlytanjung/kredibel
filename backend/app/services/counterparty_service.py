"""Clients and suppliers (spec 014, AC-014-2): read what the month run built."""

from app.domain.counterparties import Counterparty
from app.domain.errors import NotFoundError
from app.ports.counterparty_repository import CounterpartyRepository
from app.ports.workspace_repository import WorkspaceRepository


class CounterpartyService:
    def __init__(
        self, *, counterparties: CounterpartyRepository, workspaces: WorkspaceRepository
    ) -> None:
        self._counterparties = counterparties
        self._workspaces = workspaces

    async def currency(self, org_id: str) -> str:
        workspace = await self._workspaces.get_workspace(org_id)
        return workspace.currency if workspace else "IDR"

    async def list_counterparties(
        self,
        org_id: str,
        *,
        role: str | None,
        q: str | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[Counterparty], str | None]:
        return await self._counterparties.list_counterparties(
            org_id, role=role, q=q, limit=limit, cursor=cursor
        )

    async def get(self, org_id: str, counterparty_id: str) -> Counterparty:
        found = await self._counterparties.get(org_id, counterparty_id)
        if found is None:
            raise NotFoundError("Counterparty not found", code="COUNTERPARTY_NOT_FOUND")
        return found
