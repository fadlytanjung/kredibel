"""Document AI OCR (Enterprise Document OCR) as the witness of scans and photos (spec 022 phase B,
docs/07 §5.3). One page image per request; its tokens become words (domain/ocr_words.py) with
their boxes, normalized."""

import asyncio
from bisect import bisect_right

from google.api_core.client_options import ClientOptions
from google.cloud import documentai

from app.domain.ocr_words import OcrToken, ocr_words
from app.domain.verify import Word

# Bumped when the words built from the same OCR output change, so cached pages are read again.
WORDS_REVISION = 3


class DocAiOcr:
    def __init__(self, project: str, location: str, processor_id: str, version: str = "") -> None:
        self._location = location
        self._version = version or "default"
        self._client: documentai.DocumentProcessorServiceClient | None = None
        base = f"projects/{project}/locations/{location}/processors/{processor_id}"
        self._name = f"{base}/processorVersions/{version}" if version else base

    @property
    def version(self) -> str:
        return f"{self._version}.w{WORDS_REVISION}"

    def _get_client(self) -> documentai.DocumentProcessorServiceClient:
        if self._client is None:
            endpoint = f"{self._location}-documentai.googleapis.com"
            self._client = documentai.DocumentProcessorServiceClient(
                client_options=ClientOptions(api_endpoint=endpoint)
            )
        return self._client

    def _words(self, image_png: bytes) -> list[Word]:
        result = self._get_client().process_document(
            request=documentai.ProcessRequest(
                name=self._name,
                raw_document=documentai.RawDocument(content=image_png, mime_type="image/png"),
            )
        )
        return ocr_words(tokens_of(result.document))

    async def words(self, image_png: bytes) -> list[Word]:
        return await asyncio.to_thread(self._words, image_png)


def tokens_of(document: documentai.Document) -> list[OcrToken]:
    """The first page's tokens in reading order, each with its OCR line and whether a break
    follows it."""
    text = document.text
    out: list[OcrToken] = []
    for page in document.pages[:1]:
        spans = sorted(
            (int(s.start_index), int(s.end_index), n)
            for n, line in enumerate(page.lines)
            for s in line.layout.text_anchor.text_segments
        )
        starts = [s for s, _, _ in spans]
        for index, token in enumerate(page.tokens):
            segments = token.layout.text_anchor.text_segments
            vertices = token.layout.bounding_poly.normalized_vertices
            value = "".join(text[int(s.start_index) : int(s.end_index)] for s in segments).strip()
            if not value or not vertices or not segments:
                continue
            start = int(segments[0].start_index)
            at = bisect_right(starts, start) - 1
            line = spans[at][2] if at >= 0 and start < spans[at][1] else -1 - index
            xs = [v.x for v in vertices]
            ys = [v.y for v in vertices]
            space_after = (
                token.detected_break.type_
                != documentai.Document.Page.Token.DetectedBreak.Type.TYPE_UNSPECIFIED
            )
            out.append(OcrToken(value, min(xs), max(xs), min(ys), max(ys), line, space_after))
    return out
