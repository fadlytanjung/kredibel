"""An in-memory ChunkRepository (spec 022)."""

from app.domain.extraction_store import StoredChunk
from app.ports.chunk_repository import ChunkRepository


class FakeChunkRepository(ChunkRepository):
    def __init__(self) -> None:
        self.chunks: dict[str, dict[str, StoredChunk]] = {}

    async def replace_document(self, org_id: str, doc_id: str, chunks: list[StoredChunk]) -> None:
        store = self.chunks.setdefault(org_id, {})
        for key in [k for k, c in store.items() if c.doc_id == doc_id]:
            del store[key]
        store.update({c.chunk_id: c for c in chunks})

    async def list_chunks(
        self, org_id: str, doc_id: str, page_no: int | None = None
    ) -> list[StoredChunk]:
        found = [
            c
            for c in self.chunks.get(org_id, {}).values()
            if c.doc_id == doc_id and (page_no is None or c.page_no == page_no)
        ]
        return sorted(found, key=lambda c: (c.page_no, c.ordinal))

    async def delete_document(self, org_id: str, doc_id: str) -> None:
        await self.replace_document(org_id, doc_id, [])
