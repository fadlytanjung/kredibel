"""Shared reportlab setup: bundled fonts, fixed metadata, the watermark (docs/18 SD-1, SD-3).

`invariant=1` freezes reportlab's own timestamps and IDs; the creation date we want is written
through the date formatter, so the same input always gives the same bytes.
"""

import io
from collections.abc import Callable
from datetime import datetime
from functools import cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.colors import Color
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from .world import WATERMARK

FONTS_DIR = Path(__file__).resolve().parents[1] / "fonts"
FONT_FILES = {
    "DejaVuSans": "DejaVuSans.ttf",
    "DejaVuSans-Bold": "DejaVuSans-Bold.ttf",
    "DejaVuSerif": "DejaVuSerif.ttf",
    "DejaVuSerif-Bold": "DejaVuSerif-Bold.ttf",
    "DejaVuSansMono": "DejaVuSansMono.ttf",
    "DejaVuSansMono-Bold": "DejaVuSansMono-Bold.ttf",
}
_registered = False


def register_fonts() -> None:
    global _registered
    if _registered:
        return
    for name, file in FONT_FILES.items():
        pdfmetrics.registerFont(TTFont(name, str(FONTS_DIR / file)))
    _registered = True


def pdf_date(when: datetime, utc_offset_hours: int = 7) -> str:
    sign = "+" if utc_offset_hours >= 0 else "-"
    return f"D:{when:%Y%m%d%H%M%S}{sign}{abs(utc_offset_hours):02d}'00'"


def new_canvas(
    buffer: io.BytesIO,
    pagesize: tuple[float, float],
    *,
    producer: str,
    creator: str,
    title: str,
    created: datetime,
) -> Canvas:
    register_fonts()
    c = Canvas(buffer, pagesize=pagesize, invariant=1, pageCompression=1)
    c.setProducer(producer)
    c.setCreator(creator)
    c.setTitle(title)
    c.setAuthor(creator)
    c.setSubject(WATERMARK)
    stamp = pdf_date(created)
    formatter: Callable[..., str] = lambda *_parts: stamp  # noqa: E731
    c.setDateFormatter(formatter)
    return c


@cache
def _watermark_image() -> ImageReader:
    """The mark as pixels, so it is visible but stays out of the text layer: a text-layer reader
    must see the statement's values, not the watermark's letters woven through them."""
    font = ImageFont.truetype(str(FONTS_DIR / FONT_FILES["DejaVuSans-Bold"]), 120)
    left, top, right, bottom = (int(v) for v in font.getbbox(WATERMARK))
    size = (right - left + 20, bottom - top + 20)
    alpha = Image.new("L", size, 0)
    ImageDraw.Draw(alpha).text((10 - left, 10 - top), WATERMARK, fill=255, font=font)
    image = Image.new("RGBA", size, (205, 205, 205, 0))
    image.putalpha(alpha)
    return ImageReader(image)


def watermark(c: Canvas, width: float, height: float, size: float = 46) -> None:
    """The diagonal mark, drawn first so the page content sits on top of it."""
    reader = _watermark_image()
    w_px, h_px = reader.getSize()
    w = size * w_px / 120
    h = w * h_px / w_px
    c.saveState()
    c.translate(width / 2, height / 2)
    c.rotate(35)
    c.drawImage(reader, -w / 2, -h / 2, w, h, mask="auto")
    c.restoreState()


def footer(
    c: Canvas, width: float, text: str, *, page: int | None = None, pages: int | None = None
) -> None:
    c.saveState()
    c.setFont("DejaVuSans", 7)
    c.setFillColor(Color(0.35, 0.35, 0.35))
    c.drawString(36, 24, f"{WATERMARK}. {text}")
    if page is not None and pages is not None:
        c.drawRightString(width - 36, 24, f"Page {page} / {pages}")
    c.restoreState()


def text_width(text: str, font: str, size: float) -> float:
    register_fonts()
    return pdfmetrics.stringWidth(text, font, size)


def wrap(text: str, font: str, size: float, width: float) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and text_width(candidate, font, size) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]
