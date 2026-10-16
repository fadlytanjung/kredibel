"""Layout chunks: what the reader gets as context and what values are grounded in (ADR-023)."""

from app.domain.layout import chunk_page, render_chunks
from app.domain.verify import Word


def _line(top: float, *cells: tuple[str, float]) -> list[Word]:
    out = []
    for text, x in cells:
        x1 = x
        for part in text.split(" "):
            out.append(Word(part, x1, x1 + 0.01 * len(part), top, top + 0.011))
            x1 += 0.01 * len(part) + 0.004
    return out


PAGE = [
    *_line(0.05, ("Account Statement / Penyata Akaun", 0.06)),
    *_line(0.065, ("Statement Period: 16Aug26 - 15Sep26", 0.06)),
    *_line(
        0.20,
        ("Date", 0.06),
        ("Description", 0.15),
        ("Debit", 0.62),
        ("Credit", 0.74),
        ("Balance", 0.88),
    ),
    *_line(
        0.23,
        ("16Aug", 0.06),
        ("DEBITCARDTXN-DR", 0.15),
        ("3001234567", 0.45),
        ("12.40", 0.64),
        ("1,204.33", 0.88),
    ),
    *_line(0.243, ("123456 GRABRIDES-", 0.15)),
    *_line(0.256, ("MY", 0.15)),
    *_line(0.28, ("17Aug", 0.06), ("DUITNOWQRPOSCR", 0.15), ("250.00", 0.75), ("1,454.33", 0.88)),
    *_line(0.293, ("NURUL AINA", 0.15)),
    *_line(0.40, ("Total Debit", 0.40), ("12.40", 0.64)),
    *_line(0.60, ("Protected by PIDM up to RM250,000 for each depositor.", 0.06)),
]


def test_rows_start_at_dates_and_take_their_wrapped_lines():
    chunks = chunk_page(PAGE, page=2)
    rows = [c for c in chunks if c.kind == "TABLE_ROW"]
    assert [c.text.splitlines()[0].split(" | ")[0] for c in rows] == ["16Aug", "17Aug"]
    assert rows[0].text.splitlines() == [
        "16Aug | DEBITCARDTXN-DR | 3001234567 | 12.40 | 1,204.33",
        "123456 GRABRIDES-",
        "MY",
    ]
    assert len(rows[1].words) == 6


def test_header_totals_and_text_are_their_own_chunks():
    chunks = chunk_page(PAGE, page=2)
    kinds = [c.kind for c in chunks]
    assert kinds.count("TABLE_ROW") == 2
    assert "TOTALS" in kinds
    header = next(c for c in chunks if c.kind == "TABLE_HEADER")
    assert header.text == "Date | Description | Debit | Credit | Balance"
    assert any(c.kind == "TEXT" and "PIDM" in c.text for c in chunks)


def test_every_word_belongs_to_exactly_one_chunk():
    chunks = chunk_page(PAGE, page=2)
    assert sorted(id(w) for c in chunks for w in c.words) == sorted(id(w) for w in PAGE)


def test_ids_and_boxes():
    chunks = chunk_page(PAGE, page=2)
    assert [c.id for c in chunks] == [f"p2-c{i}" for i in range(1, len(chunks) + 1)]
    row = next(c for c in chunks if c.kind == "TABLE_ROW")
    assert row.bbox.y0 == 0.23 and row.bbox.y1 > 0.256


def test_the_context_the_reader_gets():
    chunks = chunk_page(PAGE, page=2)
    row = next(c for c in chunks if c.kind == "TABLE_ROW")
    text = render_chunks(chunks)
    assert f"[{row.id}] TABLE_ROW\n16Aug | DEBITCARDTXN-DR | 3001234567 | 12.40 | 1,204.33" in text


def test_a_two_line_totals_block_without_spaces_is_one_totals_chunk():
    """Real statement: `TotalCount | 123 | 4`, then `(RM) | 12,345.67 | 8,910.11` below the rows."""
    page = [
        *_line(0.23, ("15Sep", 0.06), ("C/FBALANCE", 0.15), ("1,454.33", 0.88)),
        *_line(0.245, ("TotalCount", 0.15), ("123", 0.64), ("4", 0.75)),
        *_line(0.258, ("(RM)", 0.15), ("12,345.67", 0.64), ("8,910.11", 0.75)),
    ]
    chunks = chunk_page(page, page=13)
    assert [c.kind for c in chunks] == ["TABLE_ROW", "TOTALS"]
    assert len(chunks[1].lines) == 2


def test_a_merchant_named_total_is_still_part_of_its_row():
    page = [
        *_line(
            0.23, ("16Aug", 0.06), ("DEBITCARDTXN-DR", 0.15), ("45.10", 0.64), ("1,204.33", 0.88)
        ),
        *_line(0.243, ("123456 TOTALENERGIES-", 0.15)),
        *_line(0.256, ("TOTAL PARKING SDN BHD", 0.15)),
    ]
    chunks = chunk_page(page, page=3)
    assert [c.kind for c in chunks] == ["TABLE_ROW"]


def test_chunks_survive_the_cache():
    from app.domain.layout import chunks_from_json, chunks_to_json

    chunks = chunk_page(PAGE, page=2)
    again = chunks_from_json(chunks_to_json(chunks))
    assert [(c.id, c.kind, c.text) for c in again] == [(c.id, c.kind, c.text) for c in chunks]


def test_a_tall_stray_ocr_token_does_not_join_the_line_above_it():
    from app.domain.layout import lines_of

    date = [Word("Date", 0.08, 0.16, 0.317, 0.344), Word("21/04/2026", 0.56, 0.74, 0.317, 0.344)]
    stray = Word("FOES", 0.30, 0.40, 0.3438, 0.5603)
    lines = lines_of([*date, stray])
    assert [[w.text for w in line.words] for line in lines] == [["Date", "21/04/2026"], ["FOES"]]
