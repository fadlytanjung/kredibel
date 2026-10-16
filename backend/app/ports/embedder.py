"""Port: text embeddings for verified examples (spec 016, AC-016-9; settings MODEL_EMBEDDING)."""

from typing import Protocol

DIMENSIONS = 768


class Embedder(Protocol):
    @property
    def model(self) -> str: ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """One vector of DIMENSIONS floats per text, in order."""
        ...
