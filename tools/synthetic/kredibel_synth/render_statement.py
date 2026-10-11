"""The ACB bank statement (docs/18 §3.1): one PDF per month, 2–3 pages.

Every amount is its own text object.

Returns the PDF and a sidecar map of where each amount was drawn, which T1 uses to remove and redraw
one value at exactly the same position.
"""

import hashlib
import io
from dataclasses import dataclass, field
from datetime import date, datetime

from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from . import world
from .model import BankRow, StatementData, fmt
from .pdf import footer, new_canvas, watermark, wrap

WIDTH, HEIGHT = A4
BRAND = Color(0.05, 0.33, 0.45)
GREY = Color(0.42, 0.42, 0.42)
RULE = Color(0.78, 0.8, 0.82)
BODY, BOLD, SIZE = "DejaVuSans", "DejaVuSans-Bold", 8
X_DATE, X_DESC, DESC_WIDTH = 36, 98, 205
X_DEBIT, X_CREDIT, X_BALANCE = 398, 478, 559
TOP_FIRST, TOP_NEXT, BOTTOM = 640, 720, 78
LINE, PAD = 10, 6


@dataclass(frozen=True)
class Placed:
    """Where one amount was drawn: the right edge of its text, its baseline, the font."""

    page: int
    field: str
    x_right: float
    y: float
    text: str
    font: str = BODY
    size: float = SIZE


@dataclass
class Rendered:
    pdf: bytes
    pages: int
    row_pages: dict[str, int] = field(default_factory=dict)
    amounts: dict[str, list[Placed]] = field(default_factory=dict)


def bank_reference(row: BankRow, account: str) -> str:
    digest = hashlib.sha256(f"{account}|{row.key}|{row.description}".encode()).hexdigest()
    return f"REF {row.date:%y%m%d}{int(digest[:8], 16) % 100000:05d}"


def _row_lines(row: BankRow) -> list[str]:
    return wrap(row.description, BODY, SIZE, DESC_WIDTH)


def _row_height(row: BankRow) -> float:
    return LINE * (len(_row_lines(row)) + 1) + PAD


def _paginate(st: StatementData) -> list[list[BankRow]]:
    pages: list[list[BankRow]] = [[]]
    room = TOP_FIRST - 16 - 18 - BOTTOM  # header row, opening balance row
    for row in st.rows:
        height = _row_height(row)
        if height > room:
            pages.append([])
            room = TOP_NEXT - 16 - BOTTOM
        pages[-1].append(row)
        room -= height
    if room < 74:  # the summary block needs its own space
        pages.append([])
    return pages


def _wordmark(c: Canvas, y: float) -> None:
    c.setFillColor(BRAND)
    c.roundRect(36, y - 6, 30, 30, 6, stroke=0, fill=1)
    c.setFillColor(Color(1, 1, 1))
    c.setFont(BOLD, 10)
    c.drawCentredString(51, y + 5, world.BANK_SHORT)
    c.setFillColor(BRAND)
    c.setFont(BOLD, 12.5)
    c.drawString(74, y + 10, world.BANK_NAME)
    c.setFillColor(GREY)
    c.setFont(BODY, 7.5)
    c.drawString(74, y - 1, world.BRANCH)


def _period(st: StatementData) -> str:
    return f"{st.period_start:%d %b %Y} - {st.period_end:%d %b %Y}"


def _header(c: Canvas, st: StatementData, page: int) -> float:
    _wordmark(c, 790)
    c.setFillColor(Color(0.1, 0.1, 0.1))
    c.setFont(BOLD, 13)
    title = "ACCOUNT STATEMENT" if page == 1 else "ACCOUNT STATEMENT (continued)"
    c.drawRightString(WIDTH - 36, 800, title)
    c.setFont(BODY, 8)
    c.drawRightString(WIDTH - 36, 788, f"Account {st.account_number}    Period {_period(st)}")
    if page > 1:
        return TOP_NEXT
    c.setStrokeColor(RULE)
    c.line(36, 770, WIDTH - 36, 770)
    c.setFillColor(GREY)
    c.setFont(BODY, 7)
    c.drawString(36, 755, "ACCOUNT HOLDER")
    c.drawString(330, 755, "ACCOUNT DETAILS")
    c.setFillColor(Color(0.1, 0.1, 0.1))
    c.setFont(BOLD, 9)
    c.drawString(36, 742, st.holder)
    c.setFont(BODY, 8)
    for i, line in enumerate(st.holder_address):
        c.drawString(36, 730 - i * 11, line)
    details = [
        ("Account number", st.account_number),
        ("Account type", "Business current account"),
        ("Currency", "IDR"),
        ("Period", _period(st)),
        ("Statement date", f"{st.created_at:%d %b %Y}"),
    ]
    for i, (label, value) in enumerate(details):
        c.drawString(330, 742 - i * 11, label)
        c.drawString(430, 742 - i * 11, value)
    return TOP_FIRST


def _table_header(c: Canvas, top: float) -> float:
    c.setFillColor(Color(0.93, 0.95, 0.96))
    c.rect(36, top - 4, WIDTH - 72, 16, stroke=0, fill=1)
    c.setFillColor(Color(0.1, 0.1, 0.1))
    c.setFont(BOLD, 7.5)
    c.drawString(X_DATE + 2, top + 1, "Date")
    c.drawString(X_DESC, top + 1, "Description")
    c.drawRightString(X_DEBIT, top + 1, "Debit")
    c.drawRightString(X_CREDIT, top + 1, "Credit")
    c.drawRightString(X_BALANCE - 2, top + 1, "Balance")
    return top - 16


def _amount(
    c: Canvas, out: Rendered, key: str, page: int, fld: str, x: float, y: float, value
) -> None:
    text = fmt(value)
    c.setFont(BODY, SIZE)
    c.drawRightString(x, y, text)  # one text object per amount
    out.amounts.setdefault(key, []).append(Placed(page, fld, x, y, text))


def render_statement(st: StatementData, created: datetime | None = None) -> Rendered:
    """`created` overrides the creation time (T8: the same month exported again)."""
    buffer = io.BytesIO()
    c = new_canvas(
        buffer,
        A4,
        producer=world.STATEMENT_PRODUCER,
        creator=world.STATEMENT_CREATOR,
        title=f"Account Statement {st.account_number} {st.month}",
        created=created or st.created_at,
    )
    pages = _paginate(st)
    out = Rendered(b"", len(pages))
    for page_no, rows in enumerate(pages, 1):
        watermark(c, WIDTH, HEIGHT)
        y = _table_header(c, _header(c, st, page_no))
        c.setFillColor(Color(0.1, 0.1, 0.1))
        if page_no == 1:
            c.setFont(BOLD, SIZE)
            c.drawString(X_DATE + 2, y - 2, f"{st.period_start:%d/%m/%Y}")
            c.drawString(X_DESC, y - 2, "OPENING BALANCE")
            _amount(c, out, "opening", 1, "balance", X_BALANCE - 2, y - 2, st.opening)
            y -= 18
        for row in rows:
            y = _draw_row(c, out, st, row, page_no, y)
        if page_no == len(pages):
            _summary(c, out, st, page_no, y)
        footer(
            c,
            WIDTH,
            "Computer-generated statement; no signature required.",
            page=page_no,
            pages=len(pages),
        )
        c.showPage()
    c.save()
    out.pdf = buffer.getvalue()
    return out


def _draw_row(
    c: Canvas, out: Rendered, st: StatementData, row: BankRow, page: int, y: float
) -> float:
    out.row_pages[row.key] = page
    lines = _row_lines(row)
    baseline = y - 2
    c.setFont(BODY, SIZE)
    c.setFillColor(Color(0.1, 0.1, 0.1))
    c.drawString(X_DATE + 2, baseline, f"{row.date:%d/%m/%Y}")
    for i, line in enumerate(lines):
        c.drawString(X_DESC, baseline - i * LINE, line)
    c.setFillColor(GREY)
    c.setFont(BODY, 6.5)
    c.drawString(X_DESC, baseline - len(lines) * LINE, bank_reference(row, st.account_number))
    c.setFillColor(Color(0.1, 0.1, 0.1))
    if row.debit is not None:
        _amount(c, out, row.key, page, "debit", X_DEBIT, baseline, row.debit)
    if row.credit is not None:
        _amount(c, out, row.key, page, "credit", X_CREDIT, baseline, row.credit)
    _amount(c, out, row.key, page, "balance", X_BALANCE - 2, baseline, row.balance)
    height = _row_height(row)
    c.setStrokeColor(RULE)
    c.setLineWidth(0.4)
    c.line(36, y - height + 4, WIDTH - 36, y - height + 4)
    return y - height


def _summary(c: Canvas, out: Rendered, st: StatementData, page: int, y: float) -> None:
    top = y - 14
    c.setFillColor(Color(0.93, 0.95, 0.96))
    c.rect(300, top - 50, WIDTH - 336, 60, stroke=0, fill=1)
    c.setFillColor(Color(0.1, 0.1, 0.1))
    for i, (label, value, key) in enumerate(
        [
            ("TOTAL DEBITS", st.total_debits, "total_debits"),
            ("TOTAL CREDITS", st.total_credits, "total_credits"),
            ("CLOSING BALANCE", st.closing, "closing"),
        ]
    ):
        c.setFont(BOLD if key == "closing" else BODY, SIZE)
        c.drawString(310, top - i * 16, label)
        _amount(c, out, key, page, key, X_BALANCE - 2, top - i * 16, value)


def statement_file(month: str) -> str:
    return f"statement-{month}.pdf"


def statement_date(st: StatementData) -> date:
    return st.created_at.date()
