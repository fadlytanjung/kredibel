"""Receipts (docs/18 §3.4): a till roll "photographed" as JPEG, or a clean one-page PDF e-receipt.

Every pixel of noise comes from the seeded stream, the JPEG has no EXIF and a fixed quality, so the
same receipt gives the same bytes. `photo_variant` is T10: the same paper photographed again.
"""

import io
from datetime import datetime

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.colors import Color
from reportlab.lib.units import mm

from .model import ReceiptData, fmt
from .pdf import FONTS_DIR, footer, new_canvas, watermark
from .rng import Rng
from .world import WATERMARK

ROLL_WIDTH = 600
FONT = str(FONTS_DIR / "DejaVuSansMono.ttf")
FONT_BOLD = str(FONTS_DIR / "DejaVuSansMono-Bold.ttf")
COLUMNS = 36


def _receipt_lines(rec: ReceiptData) -> list[tuple[str, bool]]:
    """(text, bold) lines of a 36-column till roll."""
    rule = "-" * COLUMNS

    def lr(left: str, right: str) -> str:
        return f"{left}{right.rjust(COLUMNS - len(left))}"

    out: list[tuple[str, bool]] = [(rec.merchant.name.upper().center(COLUMNS), True)]
    out += [(line.center(COLUMNS), False) for line in rec.merchant.address]
    out += [
        (rule, False),
        (lr("Receipt", rec.receipt_no), False),
        (lr("Date", f"{rec.issued_at:%d/%m/%Y %H:%M}"), False),
        (rule, False),
    ]
    for item in rec.items:
        out.append((item.description[:COLUMNS], False))
        out.append((lr(f"  {item.quantity} x {fmt(item.unit_price)}", fmt(item.amount)), False))
    out += [
        (rule, False),
        (lr("SUBTOTAL", fmt(rec.subtotal)), False),
        (lr(f"VAT {int(rec.vat_rate * 100)}%", fmt(rec.vat)), False),
        (lr("TOTAL", fmt(rec.total)), True),
        (rule, False),
        (lr("PAID BY", rec.payment), False),
        ("", False),
        ("Thank you for your visit".center(COLUMNS), False),
        (WATERMARK.center(COLUMNS), True),
    ]
    return out


def till_roll(rec: ReceiptData) -> Image.Image:
    font = ImageFont.truetype(FONT, 25)
    bold = ImageFont.truetype(FONT_BOLD, 25)
    lines = _receipt_lines(rec)
    height = 60 + 36 * len(lines)
    roll = Image.new("L", (ROLL_WIDTH, height), 250)
    draw = ImageDraw.Draw(roll)
    for i, (text, is_bold) in enumerate(lines):
        draw.text((22, 30 + i * 36), text, fill=20, font=bold if is_bold else font)
    _mark(roll)
    return roll


def _mark(roll: Image.Image) -> None:
    """The diagonal watermark across the paper (SD-3)."""
    layer = Image.new("L", (roll.width * 2, 120), 0)
    ImageDraw.Draw(layer).text(
        (20, 20), WATERMARK, fill=255, font=ImageFont.truetype(FONT_BOLD, 64)
    )
    layer = layer.rotate(40, expand=True, resample=Image.Resampling.BICUBIC)
    left = (roll.width - layer.width) // 2
    top = (roll.height - layer.height) // 2
    grey = Image.new("L", layer.size, 205)
    roll.paste(grey, (left, top), layer.point([v // 2 for v in range(256)]))


def _noise(rng: Rng, size: tuple[int, int], strength: int) -> Image.Image:
    raw = rng.bytes(size[0] * size[1])
    noise = Image.frombytes("L", size, raw)
    return noise.point([128 + (v - 128) * strength // 128 for v in range(256)])


def photograph(roll: Image.Image, rng: Rng, again: Rng | None = None) -> bytes:
    """Lay the paper on a table, tilt it, add perspective, grain and a little blur; JPEG q=82.

    With `again`, the same paper is photographed a second time: the framing of the first photo
    nudged a little (another angle and crop), with its own grain, so the bytes differ but a
    perceptual hash stays close (T10)."""
    angle = rng.uniform(-2.2, 2.2)
    offset = (rng.between(70, 130), rng.between(70, 130))
    skew = rng.uniform(0.00002, 0.00006)
    shear = (rng.uniform(-0.02, 0.02), rng.uniform(-0.01, 0.01))
    if again is not None:
        # Small enough that D05's perceptual hash (distance ≤ 8) still sees the same receipt.
        angle += again.uniform(-0.2, 0.2)
        offset = (offset[0] + again.between(-4, 4), offset[1] + again.between(-4, 4))
        rng = again
    canvas_w, canvas_h = roll.width + 220, roll.height + 220
    table = Image.new("RGB", (canvas_w, canvas_h), (118, 92, 70))
    grain = _noise(rng, (canvas_w, canvas_h), 40).convert("RGB")
    table = Image.blend(table, grain, 0.12)
    paper = roll.convert("RGB").rotate(
        angle, expand=True, fillcolor=(0, 0, 0), resample=Image.Resampling.BICUBIC
    )
    mask = roll.point([255] * 256).rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    table.paste(paper, offset, mask)
    coeffs = (1, shear[0], 0, shear[1], 1, 0, skew, skew / 2)
    photo = table.transform(
        table.size, Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC
    )
    photo = Image.blend(photo, _noise(rng, photo.size, 60).convert("RGB"), 0.06)
    photo = photo.filter(ImageFilter.GaussianBlur(0.6))
    out = io.BytesIO()
    photo.save(out, format="JPEG", quality=82, optimize=False, progressive=False)
    return out.getvalue()


def render_receipt_jpeg(rec: ReceiptData, rng: Rng) -> bytes:
    return photograph(till_roll(rec), rng.stream(rec.key, "photo"))


def photo_variant(rec: ReceiptData, rng: Rng) -> bytes:
    """T10: the same receipt photographed again, at another angle and crop."""
    return photograph(
        till_roll(rec), rng.stream(rec.key, "photo"), rng.stream(rec.key, "photo", "again")
    )


def render_receipt_pdf(rec: ReceiptData) -> bytes:
    lines = _receipt_lines(rec)
    width, height = 80 * mm, (24 + 4 * len(lines)) * mm
    buffer = io.BytesIO()
    c = new_canvas(
        buffer,
        (width, height),
        producer="QuickPOS e-Receipt 2.4",
        creator=rec.merchant.name,
        title=f"e-Receipt {rec.receipt_no}",
        created=datetime.combine(rec.date, rec.issued_at.time()),
    )
    watermark(c, width, height, size=16)
    c.setFillColor(Color(0.1, 0.1, 0.1))
    y = height - 18
    for text, bold in lines:
        c.setFont("DejaVuSansMono-Bold" if bold else "DejaVuSansMono", 6.6)
        c.drawString(8, y, text)
        y -= 4 * mm
    footer(c, width, "e-receipt")
    c.showPage()
    c.save()
    return buffer.getvalue()
