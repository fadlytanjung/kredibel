"""Records read from one document, replaced as a set (docs/09 §3.7): invoices and receipts."""

from typing import Any, Protocol

from app.domain.models.events import AuditEvent


class DocumentRecords[T](Protocol):
    async def replace_for_document(self, org_id: str, doc_id: str, records: list[T]) -> None:
        """Write a document's records by deterministic ID and drop the ones it no longer has."""
        ...

    async def list_records(
        self,
        org_id: str,
        *,
        doc_id: str | None = None,
        month: str | None = None,
        counterparty_id: str | None = None,
        limit: int = 200,
    ) -> list[T]: ...

    async def set_counterparties(self, org_id: str, updates: dict[str, str | None]) -> None:
        """Write the month run's counterparty per record (spec 014)."""
        ...

    async def set_held(self, org_id: str, doc_id: str, held: bool) -> None:
        """Hold or release a document's records as a possible duplicate (AC-006-5)."""
        ...

    async def get_record(self, org_id: str, record_id: str) -> T | None: ...

    async def save_correction(self, org_id: str, record: T, event: AuditEvent) -> None:
        """A person's correction of one record (T009-03a), with its audit event in one write."""
        ...

    async def set_evidence(self, org_id: str, updates: dict[str, dict[str, Any]]) -> None:
        """Write the month run's payment evidence per record (ADR-025)."""
        ...
