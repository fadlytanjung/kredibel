"""A deterministic embedder for tests: hashed bag of words, so texts sharing words are close."""

import hashlib
import math
import re

from app.ports.embedder import DIMENSIONS, Embedder


class FakeEmbedder(Embedder):
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    @property
    def model(self) -> str:
        return "fake-embedding"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        out = []
        for text in texts:
            vec = [0.0] * DIMENSIONS
            for word in re.findall(r"[a-z]{3,}", text.lower()):
                slot = int(hashlib.sha1(word.encode(), usedforsecurity=False).hexdigest()[:8], 16)
                vec[slot % DIMENSIONS] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out
