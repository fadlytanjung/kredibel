"""The reader waits out Vertex AI rate limits instead of failing the document (docs/07 §8).

A 13-page statement read 6 pages at a time hit 429 RESOURCE_EXHAUSTED; without a wait the whole
document failed.
"""

from types import SimpleNamespace
from typing import Any

import pytest
from google.genai import errors

from app.adapters.gemini_reader import GeminiDocumentReader, ReaderFailed
from app.core.settings import Settings
from app.domain.reading import DocClassification


class _Models:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = outcomes
        self.calls = 0

    async def generate_content(self, **_: Any) -> Any:
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _reader(outcomes: list[Any]) -> tuple[GeminiDocumentReader, _Models, list[float]]:
    models = _Models(outcomes)
    client = SimpleNamespace(aio=SimpleNamespace(models=models))
    waits: list[float] = []

    async def sleep(seconds: float) -> None:
        waits.append(seconds)

    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    return GeminiDocumentReader(settings, client=client, sleep=sleep), models, waits  # type: ignore[arg-type]


def _ok() -> Any:
    usage = SimpleNamespace(prompt_token_count=10, candidates_token_count=5)
    return SimpleNamespace(
        parsed=DocClassification(doc_type="RECEIPT", confidence=0.9), usage_metadata=usage
    )


def _limited() -> errors.ClientError:
    return errors.ClientError(
        429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "x"}}
    )


async def test_a_rate_limit_waits_and_retries_with_growing_pauses():
    reader, models, waits = _reader([_limited(), _limited(), _ok()])
    call = await reader.classify(b"png", "text")
    assert call.value.doc_type == "RECEIPT"
    assert models.calls == 3
    assert len(waits) == 2 and 2 <= waits[0] < waits[1] <= 30 * 1.25


async def test_a_server_error_is_retried_but_a_bad_request_fails_at_once():
    server = errors.ServerError(
        503, {"error": {"code": 503, "status": "UNAVAILABLE", "message": "x"}}
    )
    reader, _, _ = _reader([server, _ok()])
    assert (await reader.classify(b"png", "t")).value.doc_type == "RECEIPT"
    bad = errors.ClientError(
        400, {"error": {"code": 400, "status": "INVALID_ARGUMENT", "message": "x"}}
    )
    reader, models, _ = _reader([bad, _ok()])
    with pytest.raises(ReaderFailed, match="400"):
        await reader.classify(b"png", "t")
    assert models.calls == 1


async def test_rate_limit_retries_are_bounded():
    reader, models, waits = _reader([_limited() for _ in range(10)])
    with pytest.raises(ReaderFailed, match="429"):
        await reader.classify(b"png", "t")
    assert len(waits) == 6 and models.calls == 7
