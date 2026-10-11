"""Tests for content-based file type detection (AC-003-2, Spec 003 T003-01).

Accepts PDF, PNG, JPEG, CSV and XLSX detected by content; anything else returns
unsupported / raises UnsupportedMediaTypeError. A .pdf that is really a ZIP is rejected.
"""

import io
import zipfile

import pytest

from app.core.errors import UnsupportedMediaTypeError
from app.domain.file_types import (
    MediaType,
    detect_file_type,
    sniff_file_type,
)


@pytest.fixture
def minimal_pdf() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


@pytest.fixture
def minimal_png() -> bytes:
    # 8-byte signature + minimal chunk
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    )


@pytest.fixture
def minimal_jpeg() -> bytes:
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb"


@pytest.fixture
def minimal_xlsx() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types/>')
        zf.writestr("xl/workbook.xml", '<?xml version="1.0"?><workbook/>')
    return buffer.getvalue()


@pytest.fixture
def zip_not_xlsx() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("document.txt", "Hello world")
    return buffer.getvalue()


@pytest.fixture
def csv_plain() -> bytes:
    return b"Date,Description,Amount\n2026-03-01,TRANSFER OUT,32100000\n"


@pytest.fixture
def csv_with_bom() -> bytes:
    return b"\xef\xbb\xbfDate,Description,Amount\r\n2026-03-01,TRANSFER OUT,32100000\r\n"


@pytest.fixture
def csv_semicolon() -> bytes:
    return b"Date;Description;Debit;Credit\n2026-03-01;TRANSFER OUT;32100000;0\n"


def test_ac003_2_sniff_valid_pdf(minimal_pdf: bytes) -> None:
    info = sniff_file_type(minimal_pdf)
    assert info is not None
    assert info.media_type == MediaType.PDF
    assert info.extension == ".pdf"
    assert info.is_pdf is True
    assert info.is_image is False
    assert info.is_spreadsheet is False


def test_ac003_2_sniff_valid_png(minimal_png: bytes) -> None:
    info = sniff_file_type(minimal_png)
    assert info is not None
    assert info.media_type == MediaType.PNG
    assert info.extension == ".png"
    assert info.is_image is True
    assert info.is_pdf is False


def test_ac003_2_sniff_valid_jpeg(minimal_jpeg: bytes) -> None:
    info = sniff_file_type(minimal_jpeg)
    assert info is not None
    assert info.media_type == MediaType.JPEG
    assert info.extension in (".jpg", ".jpeg")
    assert info.is_image is True
    assert info.is_pdf is False


def test_ac003_2_sniff_valid_xlsx(minimal_xlsx: bytes) -> None:
    info = sniff_file_type(minimal_xlsx)
    assert info is not None
    assert info.media_type == MediaType.XLSX
    assert info.extension == ".xlsx"
    assert info.is_spreadsheet is True
    assert info.is_pdf is False


def test_ac003_2_sniff_valid_csv(csv_plain: bytes) -> None:
    info = sniff_file_type(csv_plain)
    assert info is not None
    assert info.media_type == MediaType.CSV
    assert info.extension == ".csv"
    assert info.is_spreadsheet is True


def test_ac003_2_sniff_csv_with_utf8_bom(csv_with_bom: bytes) -> None:
    info = sniff_file_type(csv_with_bom)
    assert info is not None
    assert info.media_type == MediaType.CSV
    assert info.extension == ".csv"


def test_ac003_2_sniff_csv_semicolon_delimited(csv_semicolon: bytes) -> None:
    info = sniff_file_type(csv_semicolon)
    assert info is not None
    assert info.media_type == MediaType.CSV


def test_ac003_2_zip_renamed_to_pdf_is_rejected(zip_not_xlsx: bytes) -> None:
    # A generic ZIP (even if named foo.pdf) is not an allowed type (AC-003-2)
    assert sniff_file_type(zip_not_xlsx) is None
    with pytest.raises(UnsupportedMediaTypeError):
        detect_file_type(zip_not_xlsx)


def test_ac003_2_empty_file_is_rejected() -> None:
    assert sniff_file_type(b"") is None
    with pytest.raises(UnsupportedMediaTypeError):
        detect_file_type(b"")


def test_ac003_2_random_binary_is_rejected() -> None:
    data = b"\x00\x01\x02\x03\x04\x05\x06\x07"
    assert sniff_file_type(data) is None
    with pytest.raises(UnsupportedMediaTypeError):
        detect_file_type(data)


def test_ac003_2_detect_file_type_success(minimal_pdf: bytes) -> None:
    info = detect_file_type(minimal_pdf)
    assert info.media_type == MediaType.PDF
