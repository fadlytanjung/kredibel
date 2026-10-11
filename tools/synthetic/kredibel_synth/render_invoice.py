"""Sales and purchase invoices (docs/18 §3.2, §3.3): the business's own layout and one per supplier,
each with its own font, colours and wording, so reading is not one template."""

import io
from dataclasses import dataclass
from datetime import datetime, time

from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from .model import InvoiceData, fmt
from .pdf import footer, new_canvas, watermark, wrap

WIDTH, HEIGHT = A4
INK = Color(0.1, 0.1, 0.1)
GREY = Color(0.4, 0.4, 0.4)


@dataclass(frozen=True)
class Style:
    regular: str
    bold: str
    accent: Color
    title: str
    bill_to_label: str
    producer: str
    band: bool  # a full-width colour band behind the letterhead
    boxed: bool  # table drawn in boxes instead of rules
    number_label: str
    pay_label: str


STYLES = {
    "sales": Style(
        "DejaVuSans",
        "DejaVuSans-Bold",
        Color(0.42, 0.25, 0.12),
        "INVOICE",
        "Bill to",
        "Sunrise Invoicing 1.0",
        True,
        False,
        "Invoice no.",
        "Please pay by bank transfer to",
    ),
    "gvf": Style(
        "DejaVuSerif",
        "DejaVuSerif-Bold",
        Color(0.18, 0.42, 0.2),
        "TAX INVOICE",
        "Sold to",
        "FarmBooks 2.3",
        False,
        False,
        "Invoice",
        "Remit payment to",
    ),
    "primepack": Style(
        "DejaVuSansMono",
        "DejaVuSansMono-Bold",
        Color(0.1, 0.3, 0.6),
        "INVOICE",
        "Customer",
        "PrimeERP 7.1",
        False,
        True,
        "Doc. No",
        "Bank details",
    ),
    "roastline": Style(
        "DejaVuSans",
        "DejaVuSans-Bold",
        Color(0.75, 0.33, 0.05),
        "SERVICE INVOICE",
        "Invoice to",
        "ServiceDesk Billing 4",
        True,
        True,
        "Job invoice",
        "Pay to",
    ),
    "bluewater": Style(
        "DejaVuSerif",
        "DejaVuSerif-Bold",
        Color(0.05, 0.38, 0.55),
        "COMMERCIAL INVOICE",
        "Consignee",
        "TradeLedger 3",
        True,
        False,
        "Invoice No",
        "Beneficiary",
    ),
}


def _letterhead(c: Canvas, inv: InvoiceData, s: Style) -> None:
    issuer = inv.issuer
    if s.band:
        c.setFillColor(s.accent)
        c.rect(0, HEIGHT - 96, WIDTH, 96, stroke=0, fill=1)
        c.setFillColor(Color(1, 1, 1))
    else:
        c.setStrokeColor(s.accent)
        c.setLineWidth(2)
        c.line(36, HEIGHT - 100, WIDTH - 36, HEIGHT - 100)
        c.setFillColor(s.accent)
    c.setFont(s.bold, 17)
    c.drawString(36, HEIGHT - 48, issuer.name)
    c.setFont(s.regular, 8)
    for i, line in enumerate(issuer.address):
        c.drawString(36, HEIGHT - 63 - i * 10, line)
    if issuer.tax_id:
        c.drawString(36, HEIGHT - 63 - len(issuer.address) * 10, f"Tax ID {issuer.tax_id}")
    c.setFont(s.bold, 15)
    c.drawRightString(WIDTH - 36, HEIGHT - 48, s.title)


def _meta(c: Canvas, inv: InvoiceData, s: Style) -> float:
    y = HEIGHT - 132
    c.setFillColor(GREY)
    c.setFont(s.regular, 7.5)
    c.drawString(36, y, s.bill_to_label.upper())
    c.setFillColor(INK)
    c.setFont(s.bold, 10)
    c.drawString(36, y - 14, inv.bill_to.name)
    c.setFont(s.regular, 8.5)
    lines = [*inv.bill_to.address]
    if inv.bill_to.tax_id:
        lines.append(f"Tax ID {inv.bill_to.tax_id}")
    for i, line in enumerate(lines):
        c.drawString(36, y - 27 - i * 11, line)
    rows = [
        (s.number_label, inv.number),
        ("Issue date", f"{inv.issue_date:%d %b %Y}"),
        ("Due date", f"{inv.due_date:%d %b %Y}"),
        ("Terms", f"{inv.terms_days} days"),
        ("Currency", "IDR"),
    ]
    for i, (label, value) in enumerate(rows):
        c.setFont(s.regular, 8.5)
        c.drawString(340, y - i * 13, label)
        c.setFont(s.bold if i == 0 else s.regular, 8.5)
        c.drawRightString(WIDTH - 36, y - i * 13, value)
    return y - 90


def _lines(c: Canvas, inv: InvoiceData, s: Style, top: float) -> float:
    cols = [(36, "Description"), (360, "Qty"), (455, "Unit price"), (WIDTH - 36, "Amount")]
    c.setFillColor(s.accent)
    c.rect(36, top - 5, WIDTH - 72, 17, stroke=0, fill=1)
    c.setFillColor(Color(1, 1, 1))
    c.setFont(s.bold, 8.5)
    c.drawString(40, top, cols[0][1])
    for x, label in cols[1:]:
        c.drawRightString(x - 4, top, label)
    y = top - 18
    c.setFillColor(INK)
    for line in inv.lines:
        text = wrap(line.description, s.regular, 9, 300)
        c.setFont(s.regular, 9)
        for i, part in enumerate(text):
            c.drawString(40, y - i * 11, part)
        c.drawRightString(356, y, f"{line.quantity:,}")
        c.drawRightString(451, y, fmt(line.unit_price))
        c.drawRightString(WIDTH - 40, y, fmt(line.amount))
        height = 11 * len(text) + 7
        c.setStrokeColor(Color(0.8, 0.8, 0.8))
        c.setLineWidth(0.5)
        if s.boxed:
            c.rect(36, y - height + 9, WIDTH - 72, height, stroke=1, fill=0)
        else:
            c.line(36, y - height + 9, WIDTH - 36, y - height + 9)
        y -= height
    return y


def _totals(c: Canvas, inv: InvoiceData, s: Style, y: float) -> float:
    rows = [
        ("Subtotal", inv.subtotal),
        (f"VAT {int(inv.vat_rate * 100)}%", inv.vat),
        ("TOTAL DUE", inv.total),
    ]
    y -= 8
    for i, (label, value) in enumerate(rows):
        bold = i == len(rows) - 1
        c.setFont(s.bold if bold else s.regular, 10 if bold else 9)
        c.drawString(360, y - i * 15, label)
        c.drawRightString(WIDTH - 40, y - i * 15, f"IDR {fmt(value)}" if bold else fmt(value))
    return y - 60


def _payment(c: Canvas, inv: InvoiceData, s: Style, y: float) -> None:
    c.setStrokeColor(s.accent)
    c.setLineWidth(1)
    c.rect(36, y - 46, 300, 56, stroke=1, fill=0)
    c.setFillColor(GREY)
    c.setFont(s.regular, 7.5)
    c.drawString(44, y, s.pay_label.upper())
    c.setFillColor(INK)
    c.setFont(s.regular, 9)
    c.drawString(44, y - 14, inv.pay_to.bank_name)
    c.setFont(s.bold, 9)
    c.drawString(44, y - 27, f"Account {inv.pay_to.account_number}")
    c.setFont(s.regular, 9)
    c.drawString(44, y - 40, f"Account name {inv.pay_to.holder}")
    c.setFont(s.regular, 8)
    c.drawString(350, y - 14, f"Please quote {inv.number}")
    c.drawString(350, y - 27, "with your transfer.")


def render_invoice(inv: InvoiceData) -> bytes:
    s = STYLES[inv.layout]
    buffer = io.BytesIO()
    c = new_canvas(
        buffer,
        A4,
        producer=s.producer,
        creator=inv.issuer.name,
        title=f"{s.title.title()} {inv.number}",
        created=datetime.combine(inv.issue_date, time(10, 30)),
    )
    watermark(c, WIDTH, HEIGHT)
    _letterhead(c, inv, s)
    y = _lines(c, inv, s, _meta(c, inv, s))
    y = _totals(c, inv, s, y)
    _payment(c, inv, s, y)
    footer(c, WIDTH, f"{inv.issuer.name}. Thank you for your business.")
    c.showPage()
    c.save()
    return buffer.getvalue()
