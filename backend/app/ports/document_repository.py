"""Document repository port interface (spec 003 plan).

Normative references: docs/09 §3.5, docs/10 §2.2, ADR-011.
"""

from typing import Protocol

from app.domain.models.document import Document
from app.domain.models.events import AuditEvent


class DocumentRepository(Protocol):
    async def find_original_by_sha256(self, org_id: str, sha256: str) -> Document | None:
        """Find an existing non-duplicate document in the workspace with matching SHA-256."""
        ...

    async def get_document(self, org_id: str, doc_id: str) -> Document | None:
        """Fetch a document by ID. Returns None if foreign or non-existent."""
        ...

    async def list_documents(
        self,
        org_id: str,
        *,
        doc_type: str | None = None,
        month: str | None = None,
        status: str | None = None,
        duplicate: bool | None = None,
        risk: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[Document], str | None]:
        """List documents in the workspace, newest first."""
        ...

    async def save_document(
        self,
        org_id: str,
        document: Document,
        event: AuditEvent | None = None,
    ) -> None:
        """Persist a document and optionally append an audit event."""
        ...

    async def delete_document(
        self,
        org_id: str,
        doc_id: str,
        *,
        months: list[str] | None = None,
        event: AuditEvent | None = None,
    ) -> bool:
        """Delete a document, cascade to duplicate records, and mark affected months dirty."""
        ...
