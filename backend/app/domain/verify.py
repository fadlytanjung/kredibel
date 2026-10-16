"""The AI reading against the witness words (docs/07 §6.1–§6.3). Pure: no I/O, no model.

The witness only says "these strings are printed here"; it never decides what a row is. Rows are
anchored on their printed date, values are matched inside the row's band and column, and
amount-like words nobody consumed become witness-only rows or notes. Strings compare with whitespace
removed and case folded, because text layers often drop spaces (spike S1: "16 Aug" is `16Aug`).
"""

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from statistics import median
from typing import Literal, NamedTuple, Protocol

from rapidfuzz import fuzz

Status = Literal["AGREED", "CONFLICT", "SINGLE_SOURCE", "MISSING"]
AMOUNT_FIELDS = ("debit", "credit", "balance")


class Word(NamedTuple):
    """One witness token, normalized to the page (0..1, origin top-left)."""

    text: str
    x0: float
    x1: float
    top: float
    bottom: float

    @property
    def xc(self) -> float:
        return (self.x0 + self.x1) / 2


class AiRow(NamedTuple):
    row_on_page: int
    date_text: str
    description: str
    debit_text: str | None
    credit_text: str | None
    balance_text: str | None
    chunk_ids: tuple[str, ...] = ()  # the layout chunks the values were read from (ADR-023)
    differs_from_text: tuple[str, ...] = ()  # fields where the image shows something else


class ChunkLike(Protocol):
    """A layout chunk (domain/layout.py) as grounding needs it."""

    @property
    def id(self) -> str: ...

    @property
    def kind(self) -> str: ...

    @property
    def words(self) -> list[Word]: ...


@dataclass(frozen=True)
class BBox:
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass
class FieldCheck:
    status: Status
    ai: str | None
    witness: str | None
    bbox: BBox | None


@dataclass
class VerifiedRow:
    page: int
    row_on_page: int  # printed order on the page, witness-only rows included
    source: Literal["AI", "WITNESS"]
    fields: dict[str, FieldCheck]
    notes: list[str] = field(default_factory=list)
    chunk_ids: tuple[str, ...] = ()


@dataclass
class PageVerification:
    page: int
    rows: list[VerifiedRow]
    agreed: int
    compared: int
    # Description lines at the top of the page that continue the previous page's last row.
    carry_over: str | None = None

    @property
    def agreement(self) -> float:
        return 1.0 if self.compared == 0 else self.agreed / self.compared


_AMOUNT = re.compile(
    r"^\(?-?(?:[A-Z]{1,3}\$?\.?|[$¥€£])?\s?(?:\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,]\d{1,2})?\)?(?:CR|DR|-)?$",
    re.IGNORECASE,
)
_COLUMN_TOLERANCE = 0.04  # of the page width: amounts of one column are right-aligned within this
_DATE = re.compile(
    r"^(?:\d{1,2}[/.\-]\d{1,2}(?:[/.\-]\d{2,4})?|\d{1,2}[\-]?[A-Za-z]{3,9}(?:[\-]?\d{2,4})?|\d{4}-\d{2}-\d{2})$"
)


def squash(text: str | None) -> str:
    return re.sub(r"\s+", "", text or "").casefold()


def _digits(text: str | None) -> str:
    return re.sub(r"\D", "", text or "")


def is_amount(text: str) -> bool:
    core = squash(text).upper()
    return bool(_AMOUNT.match(core)) and bool(re.search(r"[.,]", core))


def _is_date(text: str) -> bool:
    return bool(_DATE.match(squash(text)))


def _box(words: list[Word]) -> BBox | None:
    if not words:
        return None
    return BBox(
        min(w.x0 for w in words),
        min(w.top for w in words),
        max(w.x1 for w in words),
        max(w.bottom for w in words),
    )


def _same_line(a: Word, b: Word) -> bool:
    # The shorter word sets the tolerance: one tall stray token in a photo's OCR must not pull
    # the lines beside it into one.
    height = min(a.bottom - a.top, b.bottom - b.top)
    return abs(a.top - b.top) < max(0.004, height * 0.5)


def _phrases(words: list[Word]) -> list[list[Word]]:
    """Single words and neighbour pairs on a line: a date printed "16 Aug" may be two tokens."""
    ordered = sorted(words, key=lambda w: (round(w.top, 3), w.x0))
    out = [[w] for w in ordered]
    for a, b in zip(ordered, ordered[1:], strict=False):
        if _same_line(a, b) and 0 <= b.x0 - a.x1 < 0.03:
            out.append([a, b])
    return out


def _find_anchor(date_text: str, phrases: list[list[Word]], after: float) -> list[Word] | None:
    target = squash(date_text)
    hits = [p for p in phrases if p[0].top > after and squash("".join(w.text for w in p)) == target]
    return min(hits, key=lambda p: (p[0].top, p[0].x0)) if hits else None


# ---------------------------------------------------------------------------- statements


@dataclass
class _Band:
    top: float
    bottom: float
    anchor: list[Word]
    ai: AiRow | None


def merge_continuations(ai_rows: list[AiRow]) -> tuple[list[AiRow], str | None]:
    """A row with no date and no amounts is the rest of a wrapped description: it joins the row
    above, or, at the top of a page, the previous page's last row."""
    merged: list[AiRow] = []
    carry: list[str] = []
    for row in sorted(ai_rows, key=lambda r: r.row_on_page):
        is_continuation = not squash(row.date_text) and not any(
            (row.debit_text, row.credit_text, row.balance_text)
        )
        if not is_continuation:
            merged.append(row)
        elif merged:
            merged[-1] = merged[-1]._replace(
                description=f"{merged[-1].description}\n{row.description}"
            )
        else:
            carry.append(row.description)
    return merged, "\n".join(carry) or None


def verify_statement_page(
    ai_rows: list[AiRow], words: list[Word], *, page: int, totals: Sequence[str | None] = ()
) -> PageVerification:
    """`totals`: the printed totals the reader found on this page; matching words below the last
    row belong to the totals line, not to a row (verified with `verify_header`)."""
    ai_rows, carry_over = merge_continuations(ai_rows)
    words = _without_totals(words, ai_rows, totals)
    phrases = _phrases(words)

    # 1. Anchor each AI row on its printed date, in printed order.
    anchors: list[tuple[AiRow, list[Word] | None]] = []
    last = -1.0
    for row in sorted(ai_rows, key=lambda r: r.row_on_page):
        found = _find_anchor(row.date_text, phrases, last)
        anchors.append((row, found))
        if found:
            last = found[0].top
    used = {id(w) for _, a in anchors if a for w in a}
    date_x = [a[0].x0 for _, a in anchors if a]

    # 2. Witness-only rows: an unused date in the date column with an amount on its line.
    witness_anchors: list[list[Word]] = []
    if date_x:
        column = median(date_x)
        first_top = min(a[0].top for _, a in anchors if a)
        for w in words:
            if (
                id(w) in used
                or not _is_date(w.text)
                or abs(w.x0 - column) > 0.03
                or w.top < first_top
            ):
                continue
            if any(is_amount(o.text) and _same_line(o, w) for o in words):
                witness_anchors.append([w])

    # 3. Bands run from one anchor to the next, of either kind.
    starts: list[tuple[float, list[Word], AiRow | None]] = [
        (a[0].top, a, row) for row, a in anchors if a
    ]
    starts += [(a[0].top, a, None) for a in witness_anchors]
    starts.sort(key=lambda s: s[0])
    heights = [b[0] - a[0] for a, b in zip(starts, starts[1:], strict=False)]
    tail = median(heights) if heights else 0.03
    bands: list[_Band] = []
    for i, (top, anchor, row) in enumerate(starts):
        bottom = starts[i + 1][0] - 0.0005 if i + 1 < len(starts) else top + tail
        bands.append(_Band(top - 0.002, bottom, anchor, row))

    def in_band(band: _Band) -> list[Word]:
        return [w for w in words if band.top <= w.top < band.bottom]

    # 4. Learn the amount columns from values that match exactly.
    matches: dict[tuple[int, str], Word] = {}
    centres: dict[str, list[float]] = {f: [] for f in AMOUNT_FIELDS}
    for bi, band in enumerate(bands):
        if band.ai is None:
            continue
        for f in AMOUNT_FIELDS:
            value = getattr(band.ai, f"{f}_text")
            if not value:
                continue
            hit = _match_amount(value, in_band(band))
            if hit is not None:
                matches[(bi, f)] = hit
                centres[f].append(hit.xc)
    column_x = {f: median(xs) for f, xs in centres.items() if xs}

    def column_of(w: Word) -> str | None:
        """The learned column a word sits in; None when it is far from every learned column (a
        column with no exact match on this page has no position yet)."""
        if not column_x:
            return None
        nearest = min(column_x, key=lambda f: abs(column_x[f] - w.xc))
        return nearest if abs(column_x[nearest] - w.xc) <= _COLUMN_TOLERANCE else None

    def belongs(w: Word, f: str) -> bool:
        return column_of(w) == f if f in column_x else column_of(w) is None

    # 5. Status per value.
    rows: list[VerifiedRow] = []
    agreed = compared = 0
    consumed = {id(w) for w in matches.values()}
    for bi, band in enumerate(bands):
        band_words = in_band(band)
        band_box = BBox(0.0, band.top, 1.0, band.bottom)
        if band.ai is None:
            fields, n = _witness_row(band.anchor, band_words, column_of)
            rows.append(VerifiedRow(page, 0, "WITNESS", fields))
            compared += n
            continue
        ai = band.ai
        fields: dict[str, FieldCheck] = {
            "date": FieldCheck(
                "AGREED", ai.date_text, " ".join(w.text for w in band.anchor), _box(band.anchor)
            )
        }
        notes: list[str] = []
        for f in AMOUNT_FIELDS:
            value = getattr(ai, f"{f}_text")
            hit = matches.get((bi, f))
            in_column = [
                w for w in band_words if is_amount(w.text) and belongs(w, f) and w is not hit
            ]
            if value and hit is not None:
                if not belongs(hit, f):
                    fields[f] = FieldCheck("CONFLICT", value, hit.text, _box([hit]))
                else:
                    fields[f] = FieldCheck("AGREED", value, hit.text, _box([hit]))
            elif value:
                other = in_column[0] if in_column else None
                status: Status = "CONFLICT" if other else "SINGLE_SOURCE"
                fields[f] = FieldCheck(
                    status,
                    value,
                    other.text if other else None,
                    _box([other]) if other else band_box,
                )
            elif in_column:
                fields[f] = FieldCheck("CONFLICT", None, in_column[0].text, _box([in_column[0]]))
        # Two amounts printed in one cell's place (a covered value, M05 in P1).
        extra = [
            w
            for w in band_words
            if is_amount(w.text)
            and id(w) not in consumed
            and not any(c.witness == w.text for c in fields.values())
        ]
        if extra:
            notes.append("EXTRA_AMOUNT_IN_ROW")
            for w in extra:
                f = column_of(w)
                if f and f in fields and fields[f].status == "AGREED":
                    fields[f].status = "CONFLICT"
        fields["description"] = _description(ai.description, band.anchor, band_words)
        for check in fields.values():
            compared += 1
            agreed += check.status == "AGREED"
        rows.append(VerifiedRow(page, 0, "AI", fields, notes))

    unanchored = [row for row, a in anchors if a is None]
    for row in unanchored:
        fields = {
            name: FieldCheck("SINGLE_SOURCE", value, None, None)
            for name, value in (
                ("date", row.date_text),
                ("description", row.description),
                ("debit", row.debit_text),
                ("credit", row.credit_text),
                ("balance", row.balance_text),
            )
            if value
        }
        compared += len(fields)
        rows.append(VerifiedRow(page, 0, "AI", fields, ["UNANCHORED"]))

    for i, row in enumerate(rows):
        row.row_on_page = i
    return PageVerification(page, rows, agreed, compared, carry_over)


def _without_totals(
    words: list[Word], ai_rows: list[AiRow], totals: Sequence[str | None]
) -> list[Word]:
    targets = {squash(t) for t in totals if t}
    if not targets:
        return words
    dates = {squash(r.date_text) for r in ai_rows if squash(r.date_text)}
    phrases = _phrases(words)
    last_top = max(
        (p[0].top for p in phrases if squash("".join(w.text for w in p)) in dates), default=0.0
    )
    return [w for w in words if not (w.top > last_top + 0.004 and squash(w.text) in targets)]


def _match_amount(value: str, band_words: list[Word]) -> Word | None:
    target, digits = squash(value), _digits(value)
    amounts = [w for w in band_words if is_amount(w.text)]
    exact = [w for w in amounts if squash(w.text) == target]
    if exact:
        return exact[0]
    loose = [w for w in amounts if digits and _digits(w.text) == digits]
    return loose[0] if loose else None


def _description(text: str, anchor: list[Word], band_words: list[Word]) -> FieldCheck:
    read = squash(text)
    # A serial or cheque number in its own column is not part of the description the reader gives.
    rest = [
        w
        for w in band_words
        if w not in anchor
        and not is_amount(w.text)
        and not (w.text.isdigit() and len(w.text) >= 6 and w.text not in read)
    ]
    printed = "".join(w.text for w in sorted(rest, key=lambda w: (round(w.top, 3), w.x0)))
    if not printed:
        return FieldCheck("SINGLE_SOURCE", text, None, None)
    score = fuzz.partial_ratio(read, squash(printed))
    status: Status = "AGREED" if score >= 85 else "CONFLICT"
    return FieldCheck(status, text, printed, _box(rest))


def _witness_row(
    anchor: list[Word], band_words: list[Word], column_of: Callable[[Word], str | None]
) -> tuple[dict[str, FieldCheck], int]:
    """A row printed on the page that the AI reader missed: every value from the witness only."""
    fields = {"date": FieldCheck("SINGLE_SOURCE", None, anchor[0].text, _box(anchor))}
    for w in band_words:
        if is_amount(w.text):
            f = column_of(w)
            if f and f not in fields:
                fields[f] = FieldCheck("SINGLE_SOURCE", None, w.text, _box([w]))
    rest = [w for w in band_words if w not in anchor and not is_amount(w.text)]
    if rest:
        fields["description"] = FieldCheck(
            "SINGLE_SOURCE", None, " ".join(w.text for w in rest), _box(rest)
        )
    return fields, len(fields)


# ---------------------------------------------------------------------------- grounding (ADR-023)


def _date_phrase(date_text: str, words: list[Word]) -> list[Word] | None:
    target = squash(date_text)
    if not target:
        return None
    return next((p for p in _phrases(words) if squash("".join(w.text for w in p)) == target), None)


def _assign_chunks(
    ai_rows: list[AiRow], chunks: Sequence[ChunkLike]
) -> list[tuple[AiRow, list[ChunkLike]]]:
    """The chunks each row was read from: its valid citations, else the next table row with its
    date, in order (a reader that forgets to cite is still grounded)."""
    by_id = {c.id: c for c in chunks}
    order = {c.id: i for i, c in enumerate(chunks)}
    table = [c for c in chunks if c.kind == "TABLE_ROW"]
    assigned = [(row, [by_id[i] for i in row.chunk_ids if i in by_id]) for row in ai_rows]
    used = {c.id for _, cs in assigned for c in cs}
    last = -1
    for k, (row, cs) in enumerate(assigned):
        if cs:
            last = max(order[c.id] for c in cs)
            continue
        for c in table:
            if c.id in used or order[c.id] <= last:
                continue
            if _date_phrase(row.date_text, c.words):
                assigned[k] = (row, [c])
                used.add(c.id)
                last = order[c.id]
                break
    return assigned


def _ungrounded(row: AiRow, page: int) -> tuple[VerifiedRow, int]:
    values = (
        ("date", row.date_text),
        ("description", row.description),
        ("debit", row.debit_text),
        ("credit", row.credit_text),
        ("balance", row.balance_text),
    )
    fields = {name: FieldCheck("SINGLE_SOURCE", v, None, None) for name, v in values if v}
    return VerifiedRow(page, 0, "AI", fields, ["UNGROUNDED"]), len(fields)


def ground_statement_page(
    ai_rows: list[AiRow], chunks: Sequence[ChunkLike], *, page: int
) -> PageVerification:
    """Every value must be found in the words of a chunk it was read from (docs/07 §6)."""
    ai_rows, carry_over = merge_continuations(ai_rows)
    assigned = _assign_chunks(ai_rows, chunks)
    order = {c.id: i for i, c in enumerate(chunks)}

    matches: dict[tuple[int, str], Word] = {}
    centres: dict[str, list[float]] = {f: [] for f in AMOUNT_FIELDS}
    for k, (row, cs) in enumerate(assigned):
        evidence = [w for c in cs for w in c.words]
        for f in AMOUNT_FIELDS:
            value = getattr(row, f"{f}_text")
            hit = _match_amount(value, evidence) if value and evidence else None
            if hit is not None:
                matches[(k, f)] = hit
                centres[f].append(hit.xc)
    column_x = {f: median(xs) for f, xs in centres.items() if xs}

    def column_of(w: Word) -> str | None:
        if not column_x:
            return None
        nearest = min(column_x, key=lambda f: abs(column_x[f] - w.xc))
        return nearest if abs(column_x[nearest] - w.xc) <= _COLUMN_TOLERANCE else None

    def belongs(w: Word, f: str) -> bool:
        return column_of(w) == f if f in column_x else column_of(w) is None

    consumed = {id(w) for w in matches.values()}
    placed: list[tuple[float, VerifiedRow]] = []
    agreed = compared = 0
    for k, (row, cs) in enumerate(assigned):
        if not cs:
            ungrounded, n = _ungrounded(row, page)
            compared += n
            placed.append((float("inf"), ungrounded))
            continue
        evidence = [w for c in cs for w in c.words]
        anchor = _date_phrase(row.date_text, evidence) or []
        fields: dict[str, FieldCheck] = {}
        if anchor:
            printed_date = " ".join(w.text for w in anchor)
            fields["date"] = FieldCheck("AGREED", row.date_text, printed_date, _box(anchor))
        else:
            other_date = next((w for w in evidence if _is_date(w.text)), None)
            fields["date"] = FieldCheck(
                "CONFLICT" if other_date else "SINGLE_SOURCE",
                row.date_text,
                other_date.text if other_date else None,
                _box([other_date]) if other_date else None,
            )
        notes: list[str] = []
        row_box = _box(evidence)
        for f in AMOUNT_FIELDS:
            value = getattr(row, f"{f}_text")
            hit = matches.get((k, f))
            in_column = [
                w for w in evidence if is_amount(w.text) and belongs(w, f) and w is not hit
            ]
            if value and hit is not None:
                status: Status = "AGREED" if belongs(hit, f) else "CONFLICT"
                fields[f] = FieldCheck(status, value, hit.text, _box([hit]))
            elif value:
                other = in_column[0] if in_column else None
                fields[f] = FieldCheck(
                    "CONFLICT" if other else "SINGLE_SOURCE",
                    value,
                    other.text if other else None,
                    _box([other]) if other else row_box,
                )
            elif in_column:
                fields[f] = FieldCheck("CONFLICT", None, in_column[0].text, _box([in_column[0]]))
        extra = [
            w
            for w in evidence
            if is_amount(w.text)
            and id(w) not in consumed
            and not any(c.witness == w.text for c in fields.values())
        ]
        if extra:
            notes.append("EXTRA_AMOUNT_IN_ROW")
            for w in extra:
                f = column_of(w)
                if f and f in fields and fields[f].status == "AGREED":
                    fields[f].status = "CONFLICT"
        for f in row.differs_from_text:
            if f in fields:
                fields[f].status = "CONFLICT"
        if row.differs_from_text:
            notes.append("VISIBLE_DIFFERS_FROM_TEXT")
        fields["description"] = _description(row.description, anchor, evidence)
        for check in fields.values():
            compared += 1
            agreed += check.status == "AGREED"
        ids = tuple(c.id for c in cs)
        position = float(min(order[i] for i in ids))
        placed.append((position, VerifiedRow(page, 0, "AI", fields, notes, ids)))

    used = {i for _, r in placed for i in r.chunk_ids}
    for c in chunks:
        if c.kind != "TABLE_ROW" or c.id in used:
            continue
        evidence = list(c.words)
        printed = next((w for w in evidence if _is_date(w.text)), evidence[0])
        fields, n = _witness_row([printed], evidence, column_of)
        compared += n
        placed.append((float(order[c.id]), VerifiedRow(page, 0, "WITNESS", fields, [], (c.id,))))

    rows = [r for _, r in sorted(placed, key=lambda p: p[0])]
    for i, r in enumerate(rows):
        r.row_on_page = i
    return PageVerification(page, rows, agreed, compared, carry_over)


# ---------------------------------------------------------------------------- header fields


def verify_header(values: dict[str, str | None], words: list[Word]) -> dict[str, FieldCheck]:
    """Header fields searched on their page as exact strings, else digits-only (docs/07 §6.1.7)."""
    phrases = _phrases(words)
    out: dict[str, FieldCheck] = {}
    for name, value in values.items():
        if not value:
            continue
        target, digits = squash(value), _digits(value)
        hit = next((p for p in phrases if squash("".join(w.text for w in p)) == target), None)
        if hit is None and len(digits) >= 4:
            hit = next((p for p in phrases if _digits("".join(w.text for w in p)) == digits), None)
        if hit is None:
            out[name] = FieldCheck("SINGLE_SOURCE", value, None, None)
        else:
            out[name] = FieldCheck("AGREED", value, " ".join(w.text for w in hit), _box(hit))
    return out


# ---------------------------------------------------------------------------- invoices and receipts

ValueKind = Literal["text", "amount", "date"]


def _lines_of(words: list[Word]) -> list[list[Word]]:
    out: list[list[Word]] = []
    for w in sorted(words, key=lambda w: (w.top, w.x0)):
        if out and _same_line(out[-1][0], w):
            out[-1].append(w)
        else:
            out.append([w])
    return [sorted(line, key=lambda w: w.x0) for line in out]


def _span(target: str, seq: list[Word]) -> list[Word] | None:
    """Whole words of `seq` whose squashed text is exactly `target`."""
    starts: list[int] = []
    text = ""
    for w in seq:
        starts.append(len(text))
        text += squash(w.text)
    ends = [*starts[1:], len(text)]
    i = text.find(target)
    while i != -1:
        j = i + len(target)
        if i in starts and j in ends:
            return seq[starts.index(i) : ends.index(j) + 1]
        i = text.find(target, i + 1)
    return None


def _exact_word(value: str, words: list[Word]) -> Word | None:
    """A whole amount printed without separators ("15000", "1") is found as the exact word."""
    target = squash(value)
    return next((w for w in words if squash(w.text) == target), None) if target else None


def locate(value: str | None, words: list[Word]) -> list[Word] | None:
    """The words a printed value occupies: whole words on one line, or across two consecutive lines
    for a wrapped value. Compared squashed, so `ACME SDN BHD` finds `ACMESDN BHD`."""
    target = squash(value)
    if not target:
        return None
    lines = _lines_of(words)
    for seq in [*lines, *(a + b for a, b in zip(lines, lines[1:], strict=False))]:
        if hit := _span(target, seq):
            return hit
    return None


def check_value(value: str | None, kind: ValueKind, words: list[Word]) -> FieldCheck | None:
    """A header or total value found anywhere on its page (docs/07 §6.2); None when not read."""
    if not value or not value.strip():
        return None
    if kind == "amount":
        hit = _match_amount(value, words) or _exact_word(value, words)
        found = [hit] if hit else None
    else:
        found = locate(value, words)
        digits = _digits(value)
        if found is None and len(digits) >= 4:  # a date or number printed with other separators
            found = next(
                (p for p in _phrases(words) if _digits("".join(w.text for w in p)) == digits), None
            )
    if not found:
        return FieldCheck("SINGLE_SOURCE", value, None, None)
    return FieldCheck("AGREED", value, " ".join(w.text for w in found), _box(found))


@dataclass
class ItemCheck:
    """An invoice line or receipt item: its description anchors a band holding its amount."""

    description: FieldCheck
    amount: FieldCheck | None
    chunk_ids: tuple[str, ...] = ()


def check_items(items: Sequence[tuple[str, str | None]], words: list[Word]) -> list[ItemCheck]:
    """Items in printed order: each description's first line is found below the previous item, and
    its amount on the same line or the lines down to the next item (docs/07 §6.2)."""
    lines = _lines_of(words)
    anchors: list[float | None] = []
    after = -1.0
    for description, _ in items:
        first = (description or "").splitlines()[0] if description else ""
        below = [w for w in words if w.top > after]
        hit = locate(first, below)
        anchors.append(hit[0].top if hit else None)
        if hit:
            after = hit[0].top
    used: set[int] = set()
    out: list[ItemCheck] = []
    for i, (description, amount) in enumerate(items):
        top = anchors[i]
        first = (description or "").splitlines()[0] if description else ""
        if top is None:
            desc = FieldCheck("SINGLE_SOURCE", description, None, None)
            band = words
        else:
            hit = locate(first, [w for w in words if abs(w.top - top) < 0.004])
            desc = FieldCheck("AGREED", description, first, _box(hit or []))
            nxt = next((a for a in anchors[i + 1 :] if a is not None), None)
            bottom = nxt - 0.002 if nxt is not None else top + 0.06
            band = [w for line in lines if top - 0.004 <= line[0].top < bottom for w in line]
        amt: FieldCheck | None = None
        if amount:
            free = [w for w in band if id(w) not in used] or [w for w in words if id(w) not in used]
            word = _match_amount(amount, free) or _exact_word(amount, free)
            if word is not None:
                used.add(id(word))
                amt = FieldCheck("AGREED", amount, word.text, _box([word]))
            else:
                amt = FieldCheck("SINGLE_SOURCE", amount, None, None)
        out.append(ItemCheck(desc, amt))
    return out
