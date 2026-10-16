"""OCR words for a page image (spec 022 phase B, docs/07 §5.3): the witness of scans and photos."""

from typing import Protocol

from app.domain.verify import Word


class OcrText(Protocol):
    @property
    def version(self) -> str:
        """The OCR model's pinned version, part of the cache key."""
        ...

    async def words(self, image_png: bytes) -> list[Word]:
        """The page's words, normalized to the page (0..1, origin top-left), in reading order."""
        ...
