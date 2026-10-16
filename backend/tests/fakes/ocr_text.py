"""An OcrText that returns given words (spec 022 phase B) and counts its calls."""

from app.domain.verify import Word
from app.ports.ocr_text import OcrText


class FakeOcr(OcrText):
    def __init__(self, words: list[Word]) -> None:
        self._words = words
        self.calls = 0

    @property
    def version(self) -> str:
        return "fake-ocr-v1"

    async def words(self, image_png: bytes) -> list[Word]:
        self.calls += 1
        return list(self._words)
