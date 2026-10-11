"""Print and scan (docs/18 §3.7, SD-8): every page rasterized at 200 dpi, mild noise, a 0.4° skew,
written back as an image-only PDF (no text layer), so the OCR witness path is exercised."""

import io
from datetime import datetime
from typing import Any, cast

import pypdfium2 as pdfium
from PIL import Image, ImageFilter
from reportlab.lib.utils import ImageReader

from .pdf import new_canvas
from .rng import Rng

DPI = 200
SKEW_DEGREES = 0.4
SCANNER = "OfficeScan 5.2"


def _scan_page(image: Image.Image, rng: Rng) -> Image.Image:
    grey = image.convert("L")
    grey = grey.rotate(SKEW_DEGREES, expand=False, fillcolor=255, resample=Image.Resampling.BICUBIC)
    noise = Image.frombytes("L", grey.size, rng.bytes(grey.width * grey.height))
    noise = noise.point([128 + (v - 128) // 6 for v in range(256)])
    grey = Image.blend(grey, noise, 0.08).filter(ImageFilter.GaussianBlur(0.35))
    return grey


def scan_pdf(pdf: bytes, rng: Rng, *, scanned_at: datetime) -> bytes:
    source = pdfium.PdfDocument(pdf)
    buffer = io.BytesIO()
    first = source[0]
    c = new_canvas(
        buffer,
        (first.get_width(), first.get_height()),
        producer=SCANNER,
        creator=SCANNER,
        title="Scanned document",
        created=scanned_at,
    )
    for index in range(len(source)):
        page = source[index]
        width, height = page.get_width(), page.get_height()
        c.setPageSize((width, height))
        bitmap = page.render(scale=cast(Any, DPI / 72)).to_pil()  # the stub says int; floats work
        scanned = _scan_page(bitmap, rng.stream("page", index))
        jpeg = io.BytesIO()
        scanned.save(jpeg, format="JPEG", quality=80)
        c.drawImage(ImageReader(io.BytesIO(jpeg.getvalue())), 0, 0, width, height)
        c.showPage()
    c.save()
    return buffer.getvalue()
