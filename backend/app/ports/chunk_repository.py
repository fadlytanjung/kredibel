"""The stored chunks of read pages (spec 022, docs/09 §3.21)."""

from typing import Protocol

from app.domain.extraction_store import StoredChunk


class ChunkRepository(Protocol):
    async def replace_document(self, org_id: str, doc_id: str, chunks: list[StoredChunk]) -> None:
        """A document's chunks as a whole: a re-read replaces, never adds to, the earlier ones."""
        ...

    async def list_chunks(
        self, org_id: str, doc_id: str, page_no: int | None = None
    ) -> list[StoredChunk]:
        """In page and reading order."""
        ...

    async def delete_document(self, org_id: str, doc_id: str) -> None: ...
