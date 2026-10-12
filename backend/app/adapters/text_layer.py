"""The PDF text layer as positioned words (docs/07 §5.3): free, exact and inside our container."""

import io

import pdfplumber

from app.domain.verify import Word
from app.ports.page_text import PageText


class PdfTextLayer(PageText):
    def words(self, pdf: bytes) -> dict[int, list[Word]]:
        out: dict[int, list[Word]] = {}
        with pdfplumber.open(io.BytesIO(pdf)) as doc:
            for number, page in enumerate(doc.pages, 1):
                width, height = float(page.width), float(page.height)
                out[number] = [
                    Word(
                        w["text"],
                        float(w["x0"]) / width,
                        float(w["x1"]) / width,
                        float(w["top"]) / height,
                        float(w["bottom"]) / height,
                    )
                    for w in page.extract_words(keep_blank_chars=False, use_text_flow=False)
                ]
        return out
