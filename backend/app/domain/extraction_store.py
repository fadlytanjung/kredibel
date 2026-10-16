"""The extraction as records (spec 022, AC-022-1, AC-022-2). Pure.

Every layout chunk of a read page (ADR-023) becomes a stored chunk: its reading order, kind, box,
source and masked text, and its links: the fields read from it and the records (bank lines,
invoices, receipts) those values became. The page Markdown is built from these and the records, and
the document's Markdown merges its pages in order, so the same data always gives the same files.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from app.core.ids import content_id
from app.domain.accounts import mask_numbers_in_text
from app.domain.layout import Chunk

MAX_TEXT = 2000
MIN_MATCH = 3  # a printed value shorter than this is too common to link a chunk by its text
PAGE_BREAK = "\n\n---\n\n"


@dataclass(frozen=True)
class ChunkLinks:
    fields: tuple[str, ...] = ()
    tx_ids: tuple[str, ...] = ()
    invoice_ids: tuple[str, ...] = ()
    receipt_ids: tuple[str, ...] = ()
    ledger_entry_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class StoredChunk:
    chunk_id: str
    doc_id: str
    doc_type: str
    page_no: int
    ordinal: int
    layout_id: str
    kind: str
    text: str
    box: tuple[float, float, float, float] | None
    source: str
    months: tuple[str, ...]
    links: ChunkLinks = ChunkLinks()


@dataclass(frozen=True)
class PageRecord:
    """One record read from a page: what it became, how it is named, and its printed values."""

    record_id: str
    kind: str  # "tx", "invoice", "receipt"
    title: str
    printed: dict[str, tuple[str, ...]] = field(default_factory=dict)  # field → its readings
    chunk_ids: tuple[str, ...] = ()  # the layout chunks the reader cited, when kept


def chunk_id(doc_id: str, page_no: int, ordinal: int) -> str:
    return content_id("chk", doc_id, str(page_no), str(ordinal))


def _flat(text: str) -> str:
    return re.sub(r"[\s,.]", "", text).lower()


def _box(chunk: Chunk) -> tuple[float, float, float, float] | None:
    words = chunk.words
    if not words:
        return None
    return (
        round(min(w.x0 for w in words), 4),
        round(min(w.top for w in words), 4),
        round(max(w.x1 for w in words), 4),
        round(max(w.bottom for w in words), 4),
    )


def _pieces(text: str) -> list[str]:
    """A block longer than MAX_TEXT splits on line ends, in reading order."""
    if len(text) <= MAX_TEXT:
        return [text]
    out, current = [], ""
    for line in text.split("\n"):
        while len(line) > MAX_TEXT:
            if current:
                out.append(current)
                current = ""
            out.append(line[:MAX_TEXT])
            line = line[MAX_TEXT:]
        if current and len(current) + 1 + len(line) > MAX_TEXT:
            out.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        out.append(current)
    return out


def _links(layout: Chunk, records: Iterable[PageRecord]) -> ChunkLinks:
    flat = _flat(layout.text)
    ids: dict[str, list[str]] = {"tx": [], "invoice": [], "receipt": []}
    fields: list[str] = []
    for record in records:
        named = [
            name
            for name, readings in record.printed.items()
            if any(len(_flat(r)) >= MIN_MATCH and _flat(r) in flat for r in readings if r)
        ]
        cited = layout.id in record.chunk_ids
        if cited or (not record.chunk_ids and named):
            ids.setdefault(record.kind, []).append(record.record_id)
        fields += [f"{record.title} · {name}" for name in named if cited or not record.chunk_ids]
    return ChunkLinks(
        fields=tuple(dict.fromkeys(fields)),
        tx_ids=tuple(dict.fromkeys(ids["tx"])),
        invoice_ids=tuple(dict.fromkeys(ids["invoice"])),
        receipt_ids=tuple(dict.fromkeys(ids["receipt"])),
    )


def page_chunks(
    *,
    doc_id: str,
    doc_type: str,
    months: Iterable[str],
    page_no: int,
    layout: list[Chunk],
    source: str,
    records: list[PageRecord],
) -> list[StoredChunk]:
    """The page's layout chunks as stored chunks, in reading order; deterministic for the input."""
    out: list[StoredChunk] = []
    for chunk in layout:
        links = _links(chunk, records)
        for piece in _pieces(mask_numbers_in_text(chunk.text)):
            ordinal = len(out) + 1
            out.append(
                StoredChunk(
                    chunk_id=chunk_id(doc_id, page_no, ordinal),
                    doc_id=doc_id,
                    doc_type=doc_type,
                    page_no=page_no,
                    ordinal=ordinal,
                    layout_id=chunk.id,
                    kind=chunk.kind,
                    text=piece,
                    box=_box(chunk),
                    source=source,
                    months=tuple(sorted(set(months))),
                    links=links,
                )
            )
    return out


def document_markdown(pages: list[str]) -> str:
    """The whole document: its pages' Markdown in page order, each keeping its own heading."""
    return PAGE_BREAK.join(p.rstrip("\n") for p in pages if p.strip()) + "\n"
