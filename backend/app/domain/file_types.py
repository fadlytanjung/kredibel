"""Content-based file type detection (AC-003-2, docs/07 §1).

Pure domain logic. Detects PDF, PNG, JPEG, XLSX (zip with xl/workbook.xml),
and CSV (sniffed text with delimiters). Rejects generic ZIP, executables,
empty files and unknown media types with 415.
"""

import csv
import io
import zipfile
from dataclasses import dataclass
from enum import StrEnum

from app.domain.errors import UnsupportedMediaTypeError


class MediaType(StrEnum):
    PDF = "application/pdf"
    PNG = "image/png"
    JPEG = "image/jpeg"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    CSV = "text/csv"


@dataclass(frozen=True)
class FileTypeInfo:
    media_type: MediaType
    extension: str

    @property
    def is_image(self) -> bool:
        return self.media_type in (MediaType.PNG, MediaType.JPEG)

    @property
    def is_spreadsheet(self) -> bool:
        return self.media_type in (MediaType.XLSX, MediaType.CSV)

    @property
    def is_pdf(self) -> bool:
        return self.media_type == MediaType.PDF


_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"
_PDF_MAGIC = b"%PDF-"
_ZIP_MAGICS = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
_UTF8_BOM = b"\xef\xbb\xbf"


def _is_xlsx(data: bytes) -> bool:
    """True only if the bytes form a valid ZIP containing xl/workbook.xml."""
    if not any(data.startswith(magic) for magic in _ZIP_MAGICS):
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            return "xl/workbook.xml" in zf.namelist()
    except (zipfile.BadZipFile, zipfile.LargeZipFile, KeyError):
        return False


def _is_csv(data: bytes) -> bool:
    """True if data is text containing CSV/TSV delimiters (comma, semicolon, tab)."""
    if not data:
        return False

    # Binary check: null bytes in sample indicate binary data
    sample_bytes = data[:4096]
    if b"\x00" in sample_bytes:
        return False

    # Magic byte check: must not match known binary signatures
    if (
        sample_bytes.startswith(_PDF_MAGIC)
        or sample_bytes.startswith(_PNG_MAGIC)
        or sample_bytes.startswith(_JPEG_MAGIC)
    ):
        return False
    if any(sample_bytes.startswith(magic) for magic in _ZIP_MAGICS):
        return False

    # Decode text (strip UTF-8 BOM if present)
    content = data
    if content.startswith(_UTF8_BOM):
        content = content[len(_UTF8_BOM):]

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return False

    if not text.strip():
        return False

    # Check printability
    sample_text = text[:8192]
    printable_count = sum(1 for ch in sample_text if ch.isprintable() or ch in "\r\n\t")
    if printable_count / len(sample_text) < 0.95:
        return False

    # HTML / XML / JSON reject
    stripped = sample_text.lstrip()
    if stripped.startswith(("<!DOCTYPE", "<html", "<?xml", "{", "[")):
        return False

    # Delimiter sniff
    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters=",;\t")
        if dialect.delimiter in (",", ";", "\t"):
            return True
    except csv.Error:
        pass

    # Fallback: check non-empty lines having consistent delimiters
    lines = [line for line in sample_text.splitlines() if line.strip()]
    if lines:
        for delim in (",", ";", "\t"):
            if delim in lines[0]:
                return True

    return False


def sniff_file_type(data: bytes) -> FileTypeInfo | None:
    """Sniff the media type from content bytes. Returns None if unsupported or empty."""
    if not data:
        return None

    if data.startswith(_PDF_MAGIC):
        return FileTypeInfo(media_type=MediaType.PDF, extension=".pdf")

    if data.startswith(_PNG_MAGIC):
        return FileTypeInfo(media_type=MediaType.PNG, extension=".png")

    if data.startswith(_JPEG_MAGIC):
        return FileTypeInfo(media_type=MediaType.JPEG, extension=".jpg")

    if _is_xlsx(data):
        return FileTypeInfo(media_type=MediaType.XLSX, extension=".xlsx")

    if _is_csv(data):
        return FileTypeInfo(media_type=MediaType.CSV, extension=".csv")

    return None


def detect_file_type(data: bytes) -> FileTypeInfo:
    """Detect the media type from content bytes. Raises UnsupportedMediaTypeError if unsupported."""
    info = sniff_file_type(data)
    if info is None:
        raise UnsupportedMediaTypeError()
    return info
