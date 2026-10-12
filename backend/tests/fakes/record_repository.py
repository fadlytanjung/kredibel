"""In-memory invoices and receipts for tests."""

from collections.abc import Callable
from typing import Any

from app.domain.models.invoice import Invoice, Receipt
from app.ports.record_repository import DocumentRecords


class FakeRecords[T](DocumentRecords[T]):
    def __init__(self, record_id: Callable[[T], str], order: Callable[[T], Any] = str) -> None:
        self._id = record_id
        self._order = order
        self.records: dict[tuple[str, str], T] = {}
        self.held: set[tuple[str, str]] = set()

    async def replace_for_document(self, org_id: str, doc_id: str, records: list[T]) -> None:
        for key in [k for k, v in self.records.items() if k[0] == org_id and v.doc_id == doc_id]:  # type: ignore[attr-defined]
            del self.records[key]
        for record in records:
            self.records[(org_id, self._id(record))] = record

    async def list_records(
        self, org_id: str, *, doc_id: str | None = None, month: str | None = None, limit: int = 200
    ) -> list[T]:
        found = [
            v
            for (o, _), v in self.records.items()
            if o == org_id
            and (doc_id is None or v.doc_id == doc_id)  # type: ignore[attr-defined]
            and (month is None or v.month == month)  # type: ignore[attr-defined]
        ]
        return sorted(found, key=self._order)[:limit]

    async def set_held(self, org_id: str, doc_id: str, held: bool) -> None:
        (self.held.add if held else self.held.discard)((org_id, doc_id))


def fake_invoices() -> FakeRecords[Invoice]:
    return FakeRecords[Invoice](lambda i: i.invoice_id, lambda i: i.invoice_id)


def fake_receipts() -> FakeRecords[Receipt]:
    return FakeRecords[Receipt](lambda r: r.receipt_id, lambda r: r.receipt_id)
