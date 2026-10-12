"""Reading bank lines for the API (docs/10 §2.4): money in the workspace's currency (ADR-020)."""

from app.domain.models.bank_line import BankLine
from app.ports.bank_line_repository import BankLineRepository
from app.ports.workspace_repository import WorkspaceRepository


class BankLineService:
    def __init__(self, *, bank_lines: BankLineRepository, workspaces: WorkspaceRepository) -> None:
        self._lines = bank_lines
        self._workspaces = workspaces

    async def list_lines(
        self, org_id: str, *, doc_id: str | None, month: str | None, limit: int
    ) -> tuple[list[BankLine], str]:
        workspace = await self._workspaces.get_workspace(org_id)
        currency = workspace.currency if workspace else "IDR"
        return await self._lines.list_lines(
            org_id, doc_id=doc_id, month=month, limit=limit
        ), currency
