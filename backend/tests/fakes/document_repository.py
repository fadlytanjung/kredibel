"""In-memory fake document repository for tests."""

from app.domain.models.document import Document
from app.domain.models.events import AuditEvent
from app.ports.document_repository import DocumentRepository


class FakeDocumentRepository(DocumentRepository):
    def __init__(self) -> None:
        self.documents: dict[tuple[str, str], Document] = {}
        self.events: list[tuple[str, AuditEvent]] = []
        self.dirty_months: dict[tuple[str, str], int] = {}

    async def find_original_by_sha256(self, org_id: str, sha256: str) -> Document | None:
        for (doc_org, _), doc in self.documents.items():
            if doc_org == org_id and doc.sha256 == sha256 and not doc.duplicate:
                return doc
        return None

    async def get_document(self, org_id: str, doc_id: str) -> Document | None:
        return self.documents.get((org_id, doc_id))

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
        docs = [doc for (o, _), doc in self.documents.items() if o == org_id]
        if doc_type:
            docs = [d for d in docs if d.doc_type == doc_type]
        if month:
            docs = [d for d in docs if month in d.months]
        if status:
            docs = [d for d in docs if d.status == status]
        if duplicate is not None:
            docs = [d for d in docs if (d.duplicate is not None) == duplicate]
        if risk and any(d.risk for d in docs):
            docs = [d for d in docs if d.risk and d.risk.get("level") == risk]

        # Sort newest first
        docs.sort(key=lambda d: d.uploaded_at, reverse=True)
        return docs[:limit], None

    async def save_document(
        self,
        org_id: str,
        document: Document,
        event: AuditEvent | None = None,
    ) -> None:
        self.documents[(org_id, document.doc_id)] = document
        if event:
            self.events.append((org_id, event))

    async def delete_document(
        self,
        org_id: str,
        doc_id: str,
        *,
        months: list[str] | None = None,
        event: AuditEvent | None = None,
    ) -> bool:
        target = self.documents.get((org_id, doc_id))
        if target is None:
            return False

        # Cascade: delete any duplicate records that point to this doc as original (AC-003-10)
        duplicates_to_delete = [
            d_id
            for (o, d_id), doc in self.documents.items()
            if o == org_id and doc.duplicate and doc.duplicate.of_doc_id == doc_id
        ]
        for d_id in duplicates_to_delete:
            self.documents.pop((org_id, d_id), None)

        del self.documents[(org_id, doc_id)]

        # Mark months dirty
        affected_months = list(months or [])
        if target.months:
            for m in target.months:
                if m not in affected_months:
                    affected_months.append(m)

        for m in affected_months:
            gen = self.dirty_months.get((org_id, m), 0) + 1
            self.dirty_months[(org_id, m)] = gen

        if event:
            self.events.append((org_id, event))
        return True
