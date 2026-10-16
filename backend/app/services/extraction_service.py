"""The extraction store (spec 022, AC-022-1…3): a read document's chunks and Markdown, built from
what is stored about it (its records, reading details, page types and layout chunks), with no model
call. The reading step builds it after verifying; older documents get it on their first request or
from a rebuild. Layout chunks come from the extraction cache, else from the stored PDF's text layer;
a photo or scan has none until the OCR witness (phase B)."""

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import PurePosixPath
from typing import Any

import structlog

from app.core.auth import Principal
from app.domain.errors import ForbiddenError, NotFoundError, WorkspaceRequiredError
from app.domain.extraction_markdown import (
    PageExtraction,
    RecordReading,
    ValueReading,
    page_markdown,
)
from app.domain.extraction_store import PageRecord, StoredChunk, document_markdown, page_chunks
from app.domain.label_sync import model_reading
from app.domain.layout import Chunk, chunk_page, chunks_from_json, chunks_to_json
from app.domain.models.document import DocStatus, DocType, Document, TextLayerStatus
from app.domain.models.invoice import Invoice, Receipt
from app.domain.page_triage import WitnessType
from app.ports.bank_line_repository import BankLineRepository
from app.ports.chunk_repository import ChunkRepository
from app.ports.document_repository import DocumentRepository
from app.ports.document_storage import DocumentStorage
from app.ports.label_repository import LabelRepository
from app.ports.page_text import PageText
from app.ports.record_repository import DocumentRecords

log = structlog.get_logger()

READ_TYPES = {
    DocType.BANK_STATEMENT,
    DocType.SALES_INVOICE,
    DocType.PURCHASE_INVOICE,
    DocType.RECEIPT,
}
NOT_READ = {DocStatus.DUPLICATE, DocStatus.QUARANTINED, DocStatus.FAILED, DocStatus.UPLOADED}
CAN_REBUILD = {"owner", "accountant"}


def chunks_key(sha256: str, page_no: int) -> str:
    """The extraction cache's key for a page's layout chunks (docs/07 §8)."""
    return f"{sha256}/p{page_no}/chunks-v1.json"


def _reading(info: dict[str, Any], source: str) -> str | None:
    raw = info.get("raw")
    value = raw.get(source) if isinstance(raw, dict) else None
    return str(value) if value is not None else None


def _printed(consensus: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    out: dict[str, tuple[str, ...]] = {}
    for name, info in consensus.items():
        if isinstance(info, dict):
            readings = tuple(r for r in (model_reading(info), _reading(info, "TEXT_LAYER")) if r)
            if readings:
                out[name] = readings
    return out


@dataclass(frozen=True)
class _PageInput:
    title: str
    consensus: dict[str, Any]
    record: PageRecord


@dataclass
class ExtractionPorts:
    storage: DocumentStorage
    page_text: PageText | None = None
    chunks: ChunkRepository | None = None
    bank_lines: BankLineRepository | None = None
    invoices: DocumentRecords[Invoice] | None = None
    receipts: DocumentRecords[Receipt] | None = None
    labels: LabelRepository | None = None


async def _layout(ports: ExtractionPorts, org_id: str, doc: Document) -> dict[int, list[Chunk]]:
    """Each read page's layout chunks: the cache, else the PDF's own text layer (then cached)."""
    pages = [p.page_no for p in doc.pages if not p.blank] or list(range(1, doc.page_count + 1))
    out: dict[int, list[Chunk]] = {}
    for page_no in pages:
        raw = await ports.storage.get_cached(org_id, chunks_key(doc.sha256, page_no))
        if raw:
            out[page_no] = chunks_from_json(json.loads(raw))
    missing = [p for p in pages if p not in out]
    if missing and ports.page_text is not None:
        extension = PurePosixPath(doc.gcs_path).suffix
        original = await ports.storage.get_original(org_id, doc.doc_id, extension)
        if original and original.startswith(b"%PDF"):
            usable = {
                p.page_no for p in doc.pages if p.text_layer == TextLayerStatus.USABLE
            } or set(missing)
            for page_no, words in ports.page_text.words(original).items():
                if page_no in missing and page_no in usable:
                    chunks = chunk_page(words, page=page_no)
                    key = chunks_key(doc.sha256, page_no)
                    await ports.storage.put_cached(
                        org_id, key, json.dumps(chunks_to_json(chunks)).encode()
                    )
                    out[page_no] = chunks
    return {p: out.get(p, []) for p in pages}


async def _records(
    ports: ExtractionPorts, org_id: str, doc: Document
) -> dict[int, list[_PageInput]]:
    by_page: dict[int, list[_PageInput]] = {}
    if doc.doc_type == DocType.BANK_STATEMENT and ports.bank_lines is not None:
        for line in await ports.bank_lines.list_lines(org_id, doc_id=doc.doc_id, limit=5000):
            title = f"Row {line.row_index}"
            consensus = dict(line.consensus or {})
            record = PageRecord(line.tx_id, "tx", title, _printed(consensus), tuple(line.chunk_ids))
            by_page.setdefault(line.page, []).append(_PageInput(title, consensus, record))
        return by_page
    store: DocumentRecords[Any] | None = None
    noun, kind = "Invoice", "invoice"
    if doc.doc_type in (DocType.SALES_INVOICE, DocType.PURCHASE_INVOICE):
        store = ports.invoices
    elif doc.doc_type == DocType.RECEIPT:
        store, noun, kind = ports.receipts, "Receipt", "receipt"
    if store is None:
        return by_page
    for rec in await store.list_records(org_id, doc_id=doc.doc_id):
        record_id = getattr(rec, "invoice_id", None) or getattr(rec, "receipt_id", "")
        title = f"{noun} {rec.number}" if rec.number else noun
        pages: dict[int, dict[str, Any]] = {}
        for name, info in (rec.consensus or {}).items():
            if isinstance(info, dict):
                pages.setdefault(int(info.get("page") or 1), {})[name] = info
        for page_no, consensus in pages.items():
            record = PageRecord(record_id, kind, title, _printed(consensus))
            by_page.setdefault(page_no, []).append(_PageInput(title, consensus, record))
    return by_page


async def _page_types(
    ports: ExtractionPorts, org_id: str, doc: Document
) -> dict[int, tuple[str, float | None]]:
    if ports.labels is None:
        return {}
    labels = await ports.labels.list_labels(org_id, task="PAGE_TYPE", doc_id=doc.doc_id, limit=None)
    return {
        int(lb.subject.page_no): (
            lb.final_value,
            float(lb.ai.confidence) if lb.ai.confidence is not None else None,
        )
        for lb in labels
        if lb.subject.page_no
    }


async def build_extraction(
    ports: ExtractionPorts,
    org_id: str,
    doc: Document,
    *,
    page_types: dict[int, tuple[str, float | None]] | None = None,
    page_agreement: dict[int, float] | None = None,
) -> int:
    """Write the document's chunks and page Markdown; the number of pages written. The reading
    step passes the page types and agreements it just computed; a rebuild reads them back."""
    if doc.status in NOT_READ or doc.doc_type not in READ_TYPES:
        return 0
    layout = await _layout(ports, org_id, doc)
    records = await _records(ports, org_id, doc)
    kinds = page_types if page_types is not None else await _page_types(ports, org_id, doc)
    reading = doc.reading or {}
    agreement_of: dict[int, Any] = {p.page_no: p.agreement for p in doc.pages}
    witness_of = {p.page_no: p.witness for p in doc.pages}
    agreement_of.update(page_agreement or {})
    stored: list[StoredChunk] = []
    for page_no, chunks in layout.items():
        inputs = records.get(page_no, [])
        kind = kinds.get(page_no)
        agreement = agreement_of.get(page_no)
        if agreement is None and reading.get("agreement") is not None:
            agreement = Decimal(str(reading["agreement"]))
        markdown = page_markdown(
            PageExtraction(
                file_name=doc.file_name,
                page_no=page_no,
                page_count=doc.page_count,
                doc_type=doc.doc_type.value,
                type_confidence=doc.type_confidence,
                method=str(reading.get("method") or ("AI_TEXT_LAYER" if chunks else "AI_ONLY")),
                agreement=Decimal(str(round(float(agreement), 4)))
                if agreement is not None
                else None,
                model=reading.get("model") or None,
                prompt_version=reading.get("promptVersion") or None,
                records=[
                    RecordReading(
                        title=i.title,
                        values=[
                            ValueReading(
                                name,
                                str(info.get("status") or "MISSING"),
                                model_reading(info),
                                _reading(info, "TEXT_LAYER"),
                            )
                            for name, info in i.consensus.items()
                            if isinstance(info, dict)
                        ],
                    )
                    for i in inputs
                ],
                witness_text="\n\n".join(c.text for c in chunks),
                page_type=kind[0] if kind else None,
                page_type_confidence=(
                    Decimal(str(round(kind[1], 4))) if kind and kind[1] is not None else None
                ),
            )
        )
        await ports.storage.put_extraction(org_id, doc.doc_id, page_no, markdown)
        stored += page_chunks(
            doc_id=doc.doc_id,
            doc_type=doc.doc_type.value,
            months=doc.months,
            page_no=page_no,
            layout=chunks,
            source="OCR" if witness_of.get(page_no) == WitnessType.OCR else "TEXT_LAYER",
            records=[i.record for i in inputs],
        )
    if ports.chunks is not None:
        await ports.chunks.replace_document(org_id, doc.doc_id, stored)
    return len(layout)


class ExtractionService:
    """The routes' side of the store: read or build on demand, and rebuild a workspace."""

    def __init__(self, *, ports: ExtractionPorts, documents: DocumentRepository) -> None:
        self._ports = ports
        self._documents = documents

    async def _document(self, principal: Principal, doc_id: str) -> tuple[str, Document]:
        if principal.org_id is None:
            raise WorkspaceRequiredError()
        doc = await self._documents.get_document(principal.org_id, doc_id)
        if doc is None:
            raise NotFoundError(detail="Document not found")
        return principal.org_id, doc

    async def page_markdown(self, principal: Principal, doc_id: str, page_no: int) -> str:
        """AC-022-2: the page as read; a page without its file is built on this first request."""
        org_id, doc = await self._document(principal, doc_id)
        if page_no < 1 or (doc.page_count > 0 and page_no > doc.page_count):
            raise NotFoundError(detail=f"Page {page_no} not found")
        text = await self._ports.storage.get_extraction(org_id, doc.doc_id, page_no)
        if text is None and await build_extraction(self._ports, org_id, doc):
            text = await self._ports.storage.get_extraction(org_id, doc.doc_id, page_no)
        if text is None:
            raise NotFoundError(detail=f"Page {page_no} has no extraction yet")
        return text

    async def document_markdown(self, principal: Principal, doc_id: str) -> str:
        """AC-022-2: every page's Markdown in order, built where missing."""
        org_id, doc = await self._document(principal, doc_id)
        pages = [p.page_no for p in doc.pages if not p.blank] or list(range(1, doc.page_count + 1))
        texts = [await self._ports.storage.get_extraction(org_id, doc.doc_id, n) for n in pages]
        if any(t is None for t in texts) and await build_extraction(self._ports, org_id, doc):
            texts = [await self._ports.storage.get_extraction(org_id, doc.doc_id, n) for n in pages]
        found = [t for t in texts if t]
        if not found:
            raise NotFoundError(detail="This document has no extraction yet")
        return document_markdown(found)

    async def chunks(
        self, principal: Principal, doc_id: str, page_no: int | None = None
    ) -> list[StoredChunk]:
        org_id, doc = await self._document(principal, doc_id)
        if self._ports.chunks is None:
            return []
        found = await self._ports.chunks.list_chunks(org_id, doc.doc_id, page_no)
        if not found and await build_extraction(self._ports, org_id, doc):
            found = await self._ports.chunks.list_chunks(org_id, doc.doc_id, page_no)
        return found

    async def rebuild_all(self, principal: Principal) -> dict[str, int]:
        """AC-022-3: every read document's chunks and Markdown, from what is stored."""
        if principal.role not in CAN_REBUILD:
            raise ForbiddenError("Only the owner or an accountant can rebuild the extractions.")
        if principal.org_id is None:
            raise WorkspaceRequiredError()
        return await rebuild_workspace(self._ports, self._documents, principal.org_id)


async def rebuild_workspace(
    ports: ExtractionPorts, documents: DocumentRepository, org_id: str
) -> dict[str, int]:
    docs, _ = await documents.list_documents(org_id, limit=500)
    counts = {"documents": 0, "pages": 0, "withoutText": 0}
    for doc in docs:
        try:
            pages = await build_extraction(ports, org_id, doc)
        except Exception:  # noqa: BLE001 - one broken document must not stop the others
            log.warning("extraction_rebuild_failed", doc_id=doc.doc_id)
            continue
        if pages:
            counts["documents"] += 1
            counts["pages"] += pages
            if ports.chunks is not None and not await ports.chunks.list_chunks(org_id, doc.doc_id):
                counts["withoutText"] += 1  # a photo or scan: its witness comes with OCR
    return counts
