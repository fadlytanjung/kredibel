"""Chunks in Firestore (spec 022, docs/09 §3.21)."""

from google.cloud.firestore import AsyncClient, FieldFilter
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector

from app.adapters.firestore.models.chunk import ChunkDoc
from app.adapters.firestore.txn import dump
from app.domain.extraction_store import ChunkLinks, StoredChunk

BATCH = 400


def _to_doc(c: StoredChunk) -> ChunkDoc:
    box: dict[str, float] | None = (
        {"x0": c.box[0], "y0": c.box[1], "x1": c.box[2], "y1": c.box[3]} if c.box else None
    )
    links = {
        "fields": list(c.links.fields),
        "txIds": list(c.links.tx_ids),
        "invoiceIds": list(c.links.invoice_ids),
        "receiptIds": list(c.links.receipt_ids),
        "ledgerEntryIds": list(c.links.ledger_entry_ids),
    }
    return ChunkDoc(
        chunk_id=c.chunk_id,
        doc_id=c.doc_id,
        doc_type=c.doc_type,
        page_no=c.page_no,
        ordinal=c.ordinal,
        layout_id=c.layout_id,
        kind=c.kind,
        text=c.text,
        box=box,
        source=c.source,
        months=list(c.months),
        links={k: v for k, v in links.items() if v},
    )


def _from_doc(d: ChunkDoc) -> StoredChunk:
    links = d.links or {}
    box = (d.box["x0"], d.box["y0"], d.box["x1"], d.box["y1"]) if d.box else None
    return StoredChunk(
        chunk_id=d.chunk_id,
        doc_id=d.doc_id,
        doc_type=d.doc_type,
        page_no=d.page_no,
        ordinal=d.ordinal,
        layout_id=d.layout_id,
        kind=d.kind,
        text=d.text,
        box=box,
        source=d.source,
        months=tuple(d.months),
        links=ChunkLinks(
            fields=tuple(links.get("fields", ())),
            tx_ids=tuple(links.get("txIds", ())),
            invoice_ids=tuple(links.get("invoiceIds", ())),
            receipt_ids=tuple(links.get("receiptIds", ())),
            ledger_entry_ids=tuple(links.get("ledgerEntryIds", ())),
        ),
    )


class FirestoreChunkRepository:
    def __init__(self, db: AsyncClient) -> None:
        self._db = db

    def _col(self, org_id: str):  # noqa: ANN202 - the SDK's collection type
        return self._db.collection("orgs").document(org_id).collection("chunks")

    async def _ids(self, org_id: str, doc_id: str) -> list[str]:
        query = self._col(org_id).where(filter=FieldFilter("docId", "==", doc_id))
        return [snap.id async for snap in query.select([]).stream()]

    async def replace_document(self, org_id: str, doc_id: str, chunks: list[StoredChunk]) -> None:
        keep = {c.chunk_id for c in chunks}
        stale = [i for i in await self._ids(org_id, doc_id) if i not in keep]
        batch, pending = self._db.batch(), 0
        for chunk_id in stale:
            batch.delete(self._col(org_id).document(chunk_id))
            pending += 1
            if pending == BATCH:
                await batch.commit()
                batch, pending = self._db.batch(), 0
        for chunk in chunks:
            batch.set(self._col(org_id).document(chunk.chunk_id), dump(_to_doc(chunk)))
            pending += 1
            if pending == BATCH:
                await batch.commit()
                batch, pending = self._db.batch(), 0
        if pending:
            await batch.commit()

    async def list_chunks(
        self, org_id: str, doc_id: str, page_no: int | None = None
    ) -> list[StoredChunk]:
        query = self._col(org_id).where(filter=FieldFilter("docId", "==", doc_id))
        if page_no is not None:
            query = query.where(filter=FieldFilter("pageNo", "==", page_no))
        chunks = [_from_doc(ChunkDoc.model_validate(s.to_dict())) async for s in query.stream()]
        return sorted(chunks, key=lambda c: (c.page_no, c.ordinal))

    async def delete_document(self, org_id: str, doc_id: str) -> None:
        await self.replace_document(org_id, doc_id, [])

    async def save_embeddings(
        self, org_id: str, vectors: dict[str, list[float]], model: str
    ) -> None:
        batch, pending = self._db.batch(), 0
        for chunk_id, vector in vectors.items():
            ref = self._col(org_id).document(chunk_id)
            batch.update(ref, {"embedding_v1": Vector(vector), "embeddingModel": model})
            pending += 1
            if pending == BATCH:
                await batch.commit()
                batch, pending = self._db.batch(), 0
        if pending:
            await batch.commit()

    async def nearest(
        self, org_id: str, vector: list[float], limit: int
    ) -> list[tuple[StoredChunk, float]]:
        query = self._col(org_id).find_nearest(
            vector_field="embedding_v1",
            query_vector=Vector(vector),
            distance_measure=DistanceMeasure.COSINE,
            limit=limit,
            distance_result_field="vectorDistance",
        )
        out: list[tuple[StoredChunk, float]] = []
        async for snap in query.stream():
            data = snap.to_dict() or {}
            distance = float(data.get("vectorDistance") or 0.0)
            out.append((_from_doc(ChunkDoc.model_validate(data)), 1.0 - distance))
        return out
