"""Invoices and receipts for the API (docs/10 §2.4): money in the record's currency, else the
workspace's (ADR-020)."""

from app.domain.models.invoice import Invoice, Receipt
from app.ports.record_repository import DocumentRecords
from app.ports.workspace_repository import WorkspaceRepository


class RecordService:
    def __init__(
        self,
        *,
        invoices: DocumentRecords[Invoice],
        receipts: DocumentRecords[Receipt],
        workspaces: WorkspaceRepository,
    ) -> None:
        self._invoices = invoices
        self._receipts = receipts
        self._workspaces = workspaces

    async def currency(self, org_id: str) -> str:
        workspace = await self._workspaces.get_workspace(org_id)
        return workspace.currency if workspace else "IDR"

    async def list_invoices(
        self, org_id: str, *, doc_id: str | None, month: str | None, kind: str | None, limit: int
    ) -> list[Invoice]:
        found = await self._invoices.list_records(org_id, doc_id=doc_id, month=month, limit=limit)
        return [i for i in found if kind is None or i.kind == kind]

    async def list_receipts(
        self, org_id: str, *, doc_id: str | None, month: str | None, limit: int
    ) -> list[Receipt]:
        return await self._receipts.list_records(org_id, doc_id=doc_id, month=month, limit=limit)
