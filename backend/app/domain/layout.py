"""Layout chunks of a page (ADR-023): the reader's context and what its values are grounded in.

Pure: positioned words in (from the PDF text layer or Document AI OCR), chunks out. A chunk is a
table row with its wrapped lines, a table header, a totals line, or a block of text, with an ID the
reader cites (`p{page}-c{n}`), its words and its box. Every word belongs to exactly one chunk.
"""

import re
from dataclasses import dataclass, field
from statistics import median
from typing import Any, Literal

from .verify import BBox, Word, is_amount, squash

ChunkKind = Literal["TABLE_HEADER", "TABLE_ROW", "TOTALS", "TEXT"]

CELL_GAP = 0.015  # of the page width: a wider gap between words starts a new cell
_DATE_START = re.compile(
    r"^(?:\d{1,2}[/.\-]\d{1,2}(?:[/.\-]\d{2,4})?|\d{1,2}[\-]?[A-Za-z]{3,9}(?:[\-]?\d{2,4})?|\d{4}-\d{2}-\d{2})$"
)
_HEADER_WORDS = {
    *("date", "tarikh", "tanggal", "description", "diskripsi", "deskripsi", "keterangan"),
    *("particulars", "debit", "credit", "kredit", "balance", "baki", "saldo", "amount"),
    *("jumlah", "withdrawal", "deposit", "reference", "ref", "cheque", "cek", "mutasi"),
}
# Matched on squashed text: text layers often drop spaces ("TotalCount", "BakiAkhir").
_TOTAL_WORDS = re.compile(r"(?i)(total|jumlah|closingbalance|bakiakhir|endingbalance)")


@dataclass
class Line:
    words: list[Word]

    @property
    def top(self) -> float:
        return min(w.top for w in self.words)

    @property
    def bottom(self) -> float:
        return max(w.bottom for w in self.words)

    @property
    def x0(self) -> float:
        return min(w.x0 for w in self.words)

    def cells(self) -> list[list[Word]]:
        ordered = sorted(self.words, key=lambda w: w.x0)
        out: list[list[Word]] = [[ordered[0]]]
        for prev, w in zip(ordered, ordered[1:], strict=False):
            if w.x0 - prev.x1 > CELL_GAP:
                out.append([w])
            else:
                out[-1].append(w)
        return out

    def text(self) -> str:
        return " | ".join(" ".join(w.text for w in cell) for cell in self.cells())

    def plain(self) -> str:
        return " ".join(w.text for w in sorted(self.words, key=lambda w: w.x0))


@dataclass
class Chunk:
    id: str
    page: int
    kind: ChunkKind
    lines: list[Line] = field(default_factory=list)

    @property
    def words(self) -> list[Word]:
        return [w for line in self.lines for w in line.words]

    @property
    def text(self) -> str:
        return "\n".join(line.text() for line in self.lines)

    @property
    def bbox(self) -> BBox:
        ws = self.words
        return BBox(
            min(w.x0 for w in ws),
            min(w.top for w in ws),
            max(w.x1 for w in ws),
            max(w.bottom for w in ws),
        )


def _height(w: Word, line: Line) -> float:
    return min(w.bottom - w.top, *(o.bottom - o.top for o in line.words))


def lines_of(words: list[Word]) -> list[Line]:
    out: list[Line] = []
    for w in sorted(words, key=lambda w: (w.top, w.x0)):
        # The shorter of the word and the line sets the tolerance, so one tall stray OCR token
        # does not join the line above it (spec 022 phase B).
        if out and abs(w.top - out[-1].top) < max(0.004, _height(w, out[-1]) * 0.5):
            out[-1].words.append(w)
        else:
            out.append(Line([w]))
    return out


def _starts_with_date(line: Line) -> bool:
    first = min(line.words, key=lambda w: w.x0)
    return bool(_DATE_START.match(squash(first.text)))


def _is_header(line: Line) -> bool:
    found = {squash(w.text).strip(":/") for w in line.words} & _HEADER_WORDS
    return len(found) >= 3


def _is_totals(line: Line) -> bool:
    """A totals line starts with its keyword and carries a number (a count or an amount); a wrapped
    merchant name such as TOTALENERGIES does neither."""
    ordered = sorted(line.words, key=lambda w: w.x0)
    starts = bool(_TOTAL_WORDS.match(squash(ordered[0].text)))
    return starts and any(re.search(r"\d", w.text) for w in ordered[1:])


def chunk_page(words: list[Word], *, page: int) -> list[Chunk]:
    lines = lines_of(words)
    if not lines:
        return []
    pitches = [b.top - a.top for a, b in zip(lines, lines[1:], strict=False)]
    pitch = median(pitches) if pitches else 0.015
    date_x = [min(ln.words, key=lambda w: w.x0).x0 for ln in lines if _starts_with_date(ln)]
    column = median(date_x) if date_x else None

    def row_start(line: Line) -> bool:
        return column is not None and _starts_with_date(line) and abs(line.x0 - column) <= 0.03

    chunks: list[Chunk] = []

    def new(kind: ChunkKind, line: Line) -> None:
        chunks.append(Chunk(f"p{page}-c{len(chunks) + 1}", page, kind, [line]))

    previous: Line | None = None
    for line in lines:
        current = chunks[-1] if chunks else None
        gap = line.top - previous.bottom if previous else 1.0
        if _is_header(line):
            if current and current.kind == "TABLE_HEADER" and gap < 1.6 * pitch:
                current.lines.append(line)
            else:
                new("TABLE_HEADER", line)
        elif row_start(line):
            new("TABLE_ROW", line)
        elif _is_totals(line):
            new("TOTALS", line)
        elif (
            current
            and current.kind == "TOTALS"
            and gap < 1.6 * pitch
            and any(is_amount(w.text) for w in line.words)
        ):
            current.lines.append(line)  # the amounts line of a two-line totals block
        elif (
            current
            and current.kind == "TABLE_ROW"
            and column is not None
            and line.x0 > column + 0.02
            and gap < 2.0 * pitch
        ):
            current.lines.append(line)  # a wrapped description
        elif current and current.kind == "TEXT" and gap < 1.6 * pitch:
            current.lines.append(line)
        else:
            new("TEXT", line)
        previous = line
    return chunks


def render_chunks(chunks: list[Chunk]) -> str:
    """The numbered context the reader gets: one block per chunk, cells separated by `|`."""
    return "\n\n".join(f"[{c.id}] {c.kind}\n{c.text}" for c in chunks)


def chunks_to_json(chunks: list[Chunk]) -> list[dict[str, Any]]:
    """The cached form of a page's chunks (docs/07 §8 extraction cache)."""
    return [
        {
            "id": c.id,
            "page": c.page,
            "kind": c.kind,
            "lines": [[list(w) for w in ln.words] for ln in c.lines],
        }
        for c in chunks
    ]


def chunks_from_json(data: list[dict[str, Any]]) -> list[Chunk]:
    out: list[Chunk] = []
    for item in data:
        lines = [
            Line(
                [Word(str(w[0]), float(w[1]), float(w[2]), float(w[3]), float(w[4])) for w in line]
            )
            for line in item["lines"]
        ]
        out.append(Chunk(str(item["id"]), int(item["page"]), item["kind"], lines))
    return out
