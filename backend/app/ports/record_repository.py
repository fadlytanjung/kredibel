"""Records read from one document, replaced as a set (docs/09 §3.7): invoices and receipts."""

from typing import Protocol


class DocumentRecords[T](Protocol):
    async def replace_for_document(self, org_id: str, doc_id: str, records: list[T]) -> None:
        """Write a document's records by deterministic ID and drop the ones it no longer has."""
        ...

    async def list_records(
        self, org_id: str, *, doc_id: str | None = None, month: str | None = None, limit: int = 200
    ) -> list[T]: ...

    async def set_held(self, org_id: str, doc_id: str, held: bool) -> None:
        """Hold or release a document's records as a possible duplicate (AC-006-5)."""
        ...

    async def get_record(self, org_id: str, record_id: str) -> T | None: ...
