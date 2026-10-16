"""The extraction as records (spec 022, AC-022-1, AC-022-2): chunk IDs are deterministic, text is
masked, links name the fields and records each chunk backs, long blocks split in order, and the
document's Markdown merges its pages. Synthetic data only."""

from app.domain.extraction_store import (
    MAX_TEXT,
    PageRecord,
    chunk_id,
    document_markdown,
    page_chunks,
)
from app.domain.layout import Chunk, Line
from app.domain.verify import Word


def row(cid: str, text: str, top: float) -> Chunk:
    words = [
        Word(w, 0.1 + i * 0.1, 0.18 + i * 0.1, top, top + 0.02) for i, w in enumerate(text.split())
    ]
    return Chunk(cid, 2, "TABLE_ROW", [Line(words)])


LAYOUT = [
    row("p2-c1", "14/03 TRANSFER IN HARBORVIEW HOTEL GROUP 7,250,000.00 42,500,000.00", 0.30),
    row("p2-c2", "15/03 TRANSFER OUT TO 0081234567720 3,180,000.00 39,320,000.00", 0.33),
]
RECORDS = [
    PageRecord(
        "tx_17", "tx", "Row 17", {"amount": ("7,250,000.00",), "date": ("14/03",)}, ("p2-c1",)
    ),
    PageRecord("tx_18", "tx", "Row 18", {"amount": ("3,180,000.00",)}, ("p2-c2",)),
]


def build():
    return page_chunks(
        doc_id="doc_mar",
        doc_type="BANK_STATEMENT",
        months=["2026-03"],
        page_no=2,
        layout=LAYOUT,
        source="TEXT_LAYER",
        records=RECORDS,
    )


def test_ac022_1_each_chunk_is_a_record_with_order_box_links_and_masked_text():
    first, second = build()
    assert first.chunk_id == chunk_id("doc_mar", 2, 1) and first.chunk_id.startswith("chk_")
    assert (first.ordinal, first.layout_id, first.kind, first.source) == (
        1,
        "p2-c1",
        "TABLE_ROW",
        "TEXT_LAYER",
    )
    assert first.box == (0.1, 0.3, 0.88, 0.32) and first.months == ("2026-03",)
    assert first.links.tx_ids == ("tx_17",) and first.links.fields == (
        "Row 17 · amount",
        "Row 17 · date",
    )
    assert "0081234567720" not in second.text and "••••7720" in second.text, "numbers masked"
    assert second.links.tx_ids == ("tx_18",)
    assert build() == [first, second], "deterministic"


def test_ac022_1_records_without_citations_link_by_their_printed_values():
    invoice = PageRecord(
        "inv_1", "invoice", "Invoice RES-0043", {"total": ("11,288,700.00",), "currency": ("IDR",)}
    )
    layout = [
        row("p1-c1", "TOTAL DUE IDR 11,288,700.00", 0.6),
        row("p1-c2", "Please quote RES-0043", 0.7),
    ]
    a, b = page_chunks(
        doc_id="doc_inv",
        doc_type="PURCHASE_INVOICE",
        months=[],
        page_no=1,
        layout=layout,
        source="TEXT_LAYER",
        records=[invoice],
    )
    assert a.links.invoice_ids == ("inv_1",) and a.links.fields == (
        "Invoice RES-0043 · total",
        "Invoice RES-0043 · currency",
    )
    assert b.links.invoice_ids == () and b.links.fields == ()


def test_ac022_1_a_long_block_splits_in_reading_order():
    words = " ".join(f"word{i:04d}" for i in range(400))
    long_chunk = Chunk(
        "p1-c1",
        1,
        "TEXT",
        [
            Line(
                [
                    Word(w, 0.1, 0.2, 0.1 + i / 1000, 0.11 + i / 1000)
                    for i, w in enumerate(words.split())
                ]
            )
        ]
        * 1,
    )
    pieces = page_chunks(
        doc_id="d",
        doc_type="RECEIPT",
        months=[],
        page_no=1,
        layout=[long_chunk],
        source="OCR",
        records=[],
    )
    assert len(pieces) > 1 and all(len(p.text) <= MAX_TEXT for p in pieces)
    assert [p.ordinal for p in pieces] == list(range(1, len(pieces) + 1))
    assert "".join(p.text for p in pieces) == long_chunk.text, "the pieces rejoin to the block"


def test_ac022_2_the_document_merges_its_pages_in_order():
    md = document_markdown(["# a.pdf, page 1 of 2\nOne\n", "# a.pdf, page 2 of 2\nTwo\n", "  "])
    assert md == "# a.pdf, page 1 of 2\nOne\n\n---\n\n# a.pdf, page 2 of 2\nTwo\n"
