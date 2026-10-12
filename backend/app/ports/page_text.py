"""A PDF's own text layer as positioned words (docs/07 §5.3). OCR for scans comes with spike S3."""

from typing import Protocol

from app.domain.verify import Word


class PageText(Protocol):
    def words(self, pdf: bytes) -> dict[int, list[Word]]:
        """Words per page (1-based), normalized to the page (0..1, origin top-left)."""
        ...
