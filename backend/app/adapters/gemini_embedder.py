"""Embeddings with the configured Gemini embedding model on Vertex AI (ADR-016, AC-016-9)."""

from google import genai
from google.genai import types

from app.core.settings import Settings
from app.ports.embedder import DIMENSIONS, Embedder


class GeminiEmbedder(Embedder):
    def __init__(self, settings: Settings, client: genai.Client | None = None) -> None:
        self._settings = settings
        self._client = client

    @property
    def model(self) -> str:
        return self._settings.model_embedding

    def _genai(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(
                vertexai=True,
                project=self._settings.google_cloud_project,
                location=self._settings.google_cloud_location,
            )
        return self._client

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        result = await self._genai().aio.models.embed_content(
            model=self.model,
            contents=list(texts),
            config=types.EmbedContentConfig(
                output_dimensionality=DIMENSIONS, task_type="SEMANTIC_SIMILARITY"
            ),
        )
        return [list(e.values or []) for e in result.embeddings or []]
