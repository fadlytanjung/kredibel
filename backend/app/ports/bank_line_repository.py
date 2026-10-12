"""Bank lines of a workspace (docs/09 §3.6)."""

from typing import Protocol

from app.domain.models.bank_line import BankLine


class BankLineRepository(Protocol):
    async def replace_document_lines(self, org_id: str, doc_id: str, lines: list[BankLine]) -> None:
        """Write a statement's lines by deterministic ID and drop lines it no longer has."""
        ...

    async def list_lines(
        self, org_id: str, *, doc_id: str | None = None, month: str | None = None, limit: int = 500
    ) -> list[BankLine]:
        """Lines in printed order (date, then row)."""
        ...

    async def set_held(self, org_id: str, doc_id: str, held: bool) -> None:
        """Hold or release a document's lines as a possible duplicate (AC-006-5)."""
        ...

    async def get_line(self, org_id: str, tx_id: str) -> BankLine | None: ...

    async def set_support(
        self, org_id: str, updates: dict[str, tuple[str, list[str], str]]
    ) -> None:
        """Write the month run's (match state, match IDs, support) per line (ADR-025)."""
        ...
