"""In-memory bank lines for tests."""

from app.domain.models.bank_line import BankLine
from app.ports.bank_line_repository import BankLineRepository


class FakeBankLineRepository(BankLineRepository):
    def __init__(self) -> None:
        self.lines: dict[tuple[str, str], BankLine] = {}
        self.held: set[tuple[str, str]] = set()

    async def replace_document_lines(self, org_id: str, doc_id: str, lines: list[BankLine]) -> None:
        for key in [k for k, v in self.lines.items() if k[0] == org_id and v.doc_id == doc_id]:
            del self.lines[key]
        for line in lines:
            self.lines[(org_id, line.tx_id)] = line

    async def list_lines(
        self, org_id: str, *, doc_id: str | None = None, month: str | None = None, limit: int = 500
    ) -> list[BankLine]:
        out = [
            v
            for (o, _), v in self.lines.items()
            if o == org_id
            and (doc_id is None or v.doc_id == doc_id)
            and (month is None or v.month == month)
        ]
        return sorted(out, key=lambda ln: (ln.date, ln.doc_id, ln.row_index))[:limit]

    async def set_held(self, org_id: str, doc_id: str, held: bool) -> None:
        (self.held.add if held else self.held.discard)((org_id, doc_id))

    async def get_line(self, org_id: str, tx_id: str) -> BankLine | None:
        return self.lines.get((org_id, tx_id))
