"""The Transactions table of a month (spec 024, AC-024-6)."""

from app.domain.categorize import CategoryPolicy
from app.domain.models.invoice import Invoice, Receipt
from app.domain.profit_loss import ProfitLossPolicy
from app.domain.transactions import TransactionRow, transaction_rows
from app.ports.bank_line_repository import BankLineRepository
from app.ports.ledger_repository import LedgerRepository
from app.ports.match_repository import MatchRepository
from app.ports.record_repository import DocumentRecords
from app.ports.workspace_repository import WorkspaceRepository


class TransactionService:
    def __init__(
        self,
        *,
        bank_lines: BankLineRepository,
        matches: MatchRepository,
        invoices: DocumentRecords[Invoice],
        receipts: DocumentRecords[Receipt],
        ledger: LedgerRepository,
        workspaces: WorkspaceRepository,
        categories: CategoryPolicy,
        profit_loss: ProfitLossPolicy,
    ) -> None:
        self._lines = bank_lines
        self._matches = matches
        self._invoices = invoices
        self._receipts = receipts
        self._ledger = ledger
        self._workspaces = workspaces
        self._categories = categories
        self._profit_loss = profit_loss

    async def month(self, org_id: str, month: str) -> tuple[str, list[TransactionRow]]:
        workspace = await self._workspaces.get_workspace(org_id)
        currency = workspace.currency if workspace else "IDR"
        lines = await self._lines.list_lines(org_id, month=month, limit=2000)
        if not lines:
            return currency, []
        rows = transaction_rows(
            lines,
            await self._matches.list_matches(org_id, month=month),
            await self._invoices.list_records(org_id, limit=2000),
            await self._receipts.list_records(org_id, limit=2000),
            await self._ledger.list_rows(org_id),
            self._categories,
            self._profit_loss,
        )
        return currency, rows
