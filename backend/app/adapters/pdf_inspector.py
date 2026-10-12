"""What a PDF's own structure says (docs/07 §3.3, docs/08 §2.4): Producer and dates, how many times
it was saved, what each later save changed, and the font of every amount-like word."""

import io
import re
from datetime import UTC, datetime, timedelta, timezone

import pdfplumber
import pikepdf

from app.domain.checks.base import PdfInfo, ValueFont
from app.domain.verify import is_amount
from app.ports.file_inspector import FileInspector

_PDF_DATE = re.compile(
    r"D:(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?(?:([Zz+\-])(\d{2})?'?(\d{2})?)?"
)


def parse_pdf_date(raw: object) -> datetime | None:
    """`D:20260404020000+07'00'` as an aware datetime; None when absent or unreadable."""
    m = _PDF_DATE.match(str(raw or ""))
    if not m:
        return None
    parts = [int(v) if v else d for v, d in zip(m.groups()[:6], (0, 1, 1, 0, 0, 0), strict=True)]
    tz = UTC
    if m[7] in ("+", "-") and m[8]:
        offset = timedelta(hours=int(m[8]), minutes=int(m[9] or 0))
        tz = timezone(offset if m[7] == "+" else -offset)
    try:
        return datetime(*parts, tzinfo=tz)  # type: ignore[misc]
    except ValueError:
        return None


def _change_kind(segment: bytes) -> str:
    if b"/ByteRange" in segment and b"/Sig" in segment:
        return "SIGNATURE"
    if b"/Contents" in segment or b"stream" in segment:
        return "CONTENT"
    if b"/Annot" in segment:
        return "ANNOTATION"
    return "OTHER"


def saves(data: bytes) -> tuple[int, tuple[str, ...]]:
    """Each save ends with %%EOF; a linearized file's first-page section is not a separate save."""
    ends = [m.end() for m in re.finditer(rb"%%EOF", data)]
    if b"/Linearized" in data[:2048] and len(ends) > 1:
        ends = ends[1:]
    if not ends:
        return 1, ()
    later = [_change_kind(data[a:b]) for a, b in zip(ends, ends[1:], strict=False)]
    return len(ends), tuple(later)


class PdfInspector(FileInspector):
    def inspect_pdf(self, data: bytes) -> PdfInfo:
        producer = creator = None
        created = modified = None
        try:
            with pikepdf.open(io.BytesIO(data)) as pdf:
                info = pdf.docinfo
                producer = str(info.get("/Producer")) if "/Producer" in info else None
                creator = str(info.get("/Creator")) if "/Creator" in info else None
                created = parse_pdf_date(info.get("/CreationDate"))
                modified = parse_pdf_date(info.get("/ModDate"))
        except pikepdf.PdfError:
            pass
        revisions, changes = saves(data)
        fonts: list[ValueFont] = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for number, page in enumerate(pdf.pages, start=1):
                w, h = float(page.width), float(page.height)
                for word in page.extract_words(extra_attrs=["fontname", "size"]):
                    if is_amount(word["text"]):
                        fonts.append(
                            ValueFont(
                                page=number,
                                text=word["text"],
                                x0=word["x0"] / w,
                                x1=word["x1"] / w,
                                top=word["top"] / h,
                                bottom=word["bottom"] / h,
                                font=str(word["fontname"]),
                                size=round(float(word["size"]), 2),
                            )
                        )
        return PdfInfo(
            producer=producer,
            creator=creator,
            created=created,
            modified=modified,
            revisions=revisions,
            revision_changes=changes,
            value_fonts=tuple(fonts),
        )
