"""Inspecting an original file's structure (docs/07 §3.3): metadata, saves, fonts of values."""

from typing import Protocol

from app.domain.checks.base import PdfInfo


class FileInspector(Protocol):
    def inspect_pdf(self, data: bytes) -> PdfInfo: ...

    def page_hash(self, image_png: bytes) -> str:
        """64-bit perceptual hash of a page image as 16 hex digits (D05, docs/08 §2.2)."""
        ...
