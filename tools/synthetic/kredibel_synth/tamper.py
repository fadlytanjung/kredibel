"""Tampering and duplicates with real-world techniques (docs/18 §4).

T1 rewrites one amount as an incremental update, the way a PDF editor saves; T8–T11 copy a document
the way it is copied in life (exported again, scanned, photographed again, keyed in twice); T12–T13
change the books themselves. Every change is recorded for truth.json, never re-derived from files.
"""

import copy
import hashlib
import io
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, cast

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    ByteStringObject,
    ContentStream,
    DictionaryObject,
    FloatObject,
    NameObject,
    NumberObject,
    TextStringObject,
)

from . import world
from .books import dedupe_bank, purchase_invoice, supplier_payment_row
from .matching_cases import amount_tolerance
from .model import Books, InvoiceData, LedgerRow, fmt
from .pdf import pdf_date, text_width
from .render_statement import Placed
from .rng import Rng

EDITOR_PRODUCER = "PDF Editor 11"


@dataclass
class TamperRecord:
    technique: str
    file: str
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------- T1


def _fonts(page: Any) -> DictionaryObject:
    resources = cast(DictionaryObject, page["/Resources"].get_object())
    return cast(DictionaryObject, resources["/Font"].get_object())


def _text_object_at(ops: list[tuple[list[Any], bytes]], x: float, y: float) -> tuple[int, int]:
    """The BT…ET object whose text matrix starts at (x, y)."""
    start = None
    for i, (operands, op) in enumerate(ops):
        if op == b"BT":
            start = i
        elif op == b"Tm" and start is not None:
            tx, ty = float(operands[4]), float(operands[5])
            if abs(tx - x) < 0.05 and abs(ty - y) < 0.05:
                end = next(j for j in range(i, len(ops)) if ops[j][1] == b"ET")
                return start, end
    raise ValueError(f"no text object at ({x:.2f}, {y:.2f})")


def edit_amount(
    pdf: bytes,
    placed: Placed,
    new_value: Decimal,
    *,
    created: datetime,
    file_id: str,
) -> bytes:
    """T1: remove one amount's text object and draw the new value in Helvetica at the same spot,
    saved as an incremental update (2 revisions) with an editor's Producer and ModDate +3 days."""
    reader = PdfReader(io.BytesIO(pdf))
    writer = PdfWriter(reader, incremental=True)
    page = writer.pages[placed.page - 1]
    content = ContentStream(page.get_contents(), writer)
    ops = list(content.operations)
    x_left = placed.x_right - text_width(placed.text, placed.font, placed.size)
    start, end = _text_object_at(ops, x_left, placed.y)
    del ops[start : end + 1]
    new_text = fmt(new_value)
    from reportlab.pdfbase.pdfmetrics import stringWidth

    x_new = placed.x_right - stringWidth(new_text, "Helvetica", placed.size)
    ops += [
        ([], b"q"),
        ([FloatObject(0.1), FloatObject(0.1), FloatObject(0.1)], b"rg"),
        ([], b"BT"),
        ([NameObject("/Helv"), FloatObject(placed.size)], b"Tf"),
        (
            [
                NumberObject(1),
                NumberObject(0),
                NumberObject(0),
                NumberObject(1),
                FloatObject(round(x_new, 2)),
                FloatObject(placed.y),
            ],
            b"Tm",
        ),
        ([TextStringObject(new_text)], b"Tj"),
        ([], b"ET"),
        ([], b"Q"),
    ]
    content.operations = ops
    page.replace_contents(content)
    fonts = _fonts(page)
    helvetica = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
            NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
        }
    )
    fonts[NameObject("/Helv")] = writer._add_object(helvetica)
    writer.add_metadata(
        {"/ModDate": pdf_date(created + timedelta(days=3)), "/Producer": EDITOR_PRODUCER}
    )
    first = reader.trailer.get("/ID")
    first_id = first[0] if first else ByteStringObject(b"")
    second_id = ByteStringObject(hashlib.sha256(file_id.encode()).digest()[:16])
    writer._ID = ArrayObject([first_id, second_id])  # a fixed second ID: same bytes every run
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def cover_amount(pdf: bytes, placed: Placed, new_value: Decimal) -> bytes:
    """White-out: a filled white rectangle over one value and a new value drawn on top, saved as a
    new file. The old characters stay in the text layer under the rectangle (M05, P1)."""
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf)))
    page = writer.pages[placed.page - 1]
    content = ContentStream(page.get_contents(), writer)
    width = text_width(placed.text, placed.font, placed.size)
    new_text = fmt(new_value)
    x_new = placed.x_right - text_width(new_text, placed.font, placed.size)
    content.operations += [
        ([], b"q"),
        ([NumberObject(1)], b"g"),
        (
            [
                FloatObject(round(placed.x_right - width - 2, 2)),
                FloatObject(placed.y - 2.5),
                FloatObject(round(width + 4, 2)),
                FloatObject(placed.size + 3),
            ],
            b"re",
        ),
        ([], b"f"),
        ([FloatObject(0.1), FloatObject(0.1), FloatObject(0.1)], b"rg"),
        ([], b"BT"),
        ([NameObject("/Helv"), FloatObject(placed.size)], b"Tf"),
        (
            [
                NumberObject(1),
                NumberObject(0),
                NumberObject(0),
                NumberObject(1),
                FloatObject(round(x_new, 2)),
                FloatObject(placed.y),
            ],
            b"Tm",
        ),
        ([TextStringObject(new_text)], b"Tj"),
        ([], b"ET"),
        ([], b"Q"),
    ]
    page.replace_contents(content)
    fonts = _fonts(page)
    fonts[NameObject("/Helv")] = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
                NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
            }
        )
    )
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def strip_unicode_maps(pdf: bytes) -> bytes:
    """cid-glyphs: drop every /ToUnicode map, so the text layer is glyph codes without meaning."""
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf)))
    for page in writer.pages:
        for ref in _fonts(page).values():
            font = ref.get_object()
            if "/ToUnicode" in font:
                del font["/ToUnicode"]
            for descendant in font.get("/DescendantFonts", []):
                d = descendant.get_object()
                if "/ToUnicode" in d:
                    del d["/ToUnicode"]
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# ---------------------------------------------------------------------------- T11


def duplicate_ledger_journal(
    ledger: list[LedgerRow], on_or_after: date
) -> tuple[list[LedgerRow], list[str]]:
    """T11: a bank journal keyed in twice (same date, accounts, amounts, reference), placed right
    after the original. Returns the new ledger (renumbered) and the keys of the copied lines."""
    target = next(
        e.journal
        for e in ledger
        if e.date >= on_or_after
        and e.journal.startswith("BNK")
        and e.account == "1110"
        and e.reference  # a typed reference, so the copy matches on every field D06 compares
    )
    month = target[4:11]
    used = [
        int(e.journal.rsplit("-", 1)[1]) for e in ledger if e.journal.startswith(f"BNK-{month}")
    ]
    new_journal = f"BNK-{month}-{max(used) + 1:03d}"
    original = [e for e in ledger if e.journal == target]
    copies = [
        LedgerRow(
            e.date,
            new_journal,
            e.account,
            e.account_name,
            e.description,
            e.reference,
            e.debit,
            e.credit,
        )
        for e in original
    ]
    last = max(i for i, e in enumerate(ledger) if e.journal == target)
    out = (
        [copy.copy(e) for e in ledger[: last + 1]]
        + copies
        + [copy.copy(e) for e in ledger[last + 1 :]]
    )
    for n, entry in enumerate(out, 1):
        entry.key = f"lg#{n}"
    return out, [e.key for e in copies]


# ---------------------------------------------------------------------------- T12, T13


def change_supplier_account(books: Books, invoice_key: str) -> InvoiceData:
    """T12: the supplier's invoice asks for a new account at another bank, and it is paid there."""
    inv = next(i for i in books.purchases if i.key == invoice_key)
    inv.pay_to = world.ROASTLINE_NEW_PAY_TO
    for row in books.bank_rows:
        if row.documents == [inv.key]:
            row.description = supplier_payment_row(inv, row.date, row.category).description
    return inv


def unpaid_supplier_invoices(books: Books, rng: Rng) -> list[InvoiceData]:
    """T13: two invoices from a supplier with no bank or ledger history, fitting no debit."""
    r = rng.stream("T13")
    added: list[InvoiceData] = []
    for seq, day in ((3, 2), (4, 16)):
        issue = date(world.YEAR, 4, day)
        inv = purchase_invoice(
            r, world.BLUEWATER, f"inv-purchase-2026-04-{seq:02d}", f"BWT/INV/26-{183 + seq}", issue
        )
        while _fits_a_debit(inv, books, added):
            first = inv.lines[0]
            inv.lines = [type(first)(first.description, first.quantity + 1, first.unit_price)]
        added.append(inv)
    books.purchases.extend(added)
    return added


def _fits_a_debit(inv: InvoiceData, books: Books, others: list[InvoiceData]) -> bool:
    window_start = inv.issue_date - timedelta(days=3)
    window_end = inv.due_date + timedelta(days=30)
    amounts = [
        r.amount
        for r in books.bank_rows
        if r.debit is not None and window_start <= r.date <= window_end
    ]
    amounts += [i.total for i in [*books.purchases, *others]]
    return any(
        abs(inv.total - a) <= max(amount_tolerance(a), amount_tolerance(inv.total)) * 3
        for a in amounts
    )


def recheck_bank(books: Books) -> None:
    rows = {m: st.rows for m, st in books.statements.items()}
    dedupe_bank(rows)
