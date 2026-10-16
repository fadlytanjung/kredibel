"""Document AI OCR (Enterprise Document OCR) as the witness of scans and photos (spec 022 phase B,
docs/07 §5.3). One page image per request; the words come with their boxes, normalized."""

import asyncio

from google.api_core.client_options import ClientOptions
from google.cloud import documentai

from app.domain.verify import Word


class DocAiOcr:
    def __init__(self, project: str, location: str, processor_id: str, version: str = "") -> None:
        self._location = location
        self._version = version or "default"
        self._client: documentai.DocumentProcessorServiceClient | None = None
        base = f"projects/{project}/locations/{location}/processors/{processor_id}"
        self._name = f"{base}/processorVersions/{version}" if version else base

    @property
    def version(self) -> str:
        return self._version

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
        document = result.document
        out: list[Word] = []
        for page in document.pages[:1]:
            for token in page.tokens:
                segments = token.layout.text_anchor.text_segments
                text = "".join(
                    document.text[int(s.start_index) : int(s.end_index)] for s in segments
                ).strip()
                vertices = token.layout.bounding_poly.normalized_vertices
                if not text or not vertices:
                    continue
                xs = [v.x for v in vertices]
                ys = [v.y for v in vertices]
                out.append(Word(text, min(xs), max(xs), min(ys), max(ys)))
        return out

    async def words(self, image_png: bytes) -> list[Word]:
        return await asyncio.to_thread(self._words, image_png)
