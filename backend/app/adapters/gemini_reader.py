"""DocumentReader on Gemini (docs/07 §4–§5, ADR-023): the instruction, the page image and the page's
chunks are separate content parts; the document never sits inside the instruction (docs/06 §6)."""

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

from app.adapters.prompt_files import Prompt, load_prompt
from app.core.settings import Settings
from app.domain.reading import (
    CategorizeResult,
    DocClassification,
    InvoicePageReading,
    ReceiptPageReading,
    StatementPageReading,
    TransactionItem,
)
from app.ports.document_reader import DocumentReader, ReaderCall

_TASKS = {
    "classify": "classify_document",
    "statement_page": "read_statement_page",
    "invoice_page": "read_invoice_page",
    "receipt_page": "read_receipt",
    "categorize": "categorize_transactions",
}


class ReaderFailed(Exception):
    pass


# 429 is Vertex AI's rate limit (RESOURCE_EXHAUSTED); 5xx are transient on its side.
_TRANSIENT = {429, 500, 502, 503, 504}


def _backoff(retry: int) -> float:
    """2, 4, 8, 16, 30 … seconds plus up to 25 % jitter, so parallel pages do not retry at once."""
    base = min(30.0, 2.0**retry)
    return base * (1 + random.random() * 0.25)


class GeminiDocumentReader(DocumentReader):
    def __init__(
        self,
        settings: Settings,
        *,
        client: genai.Client | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._settings = settings
        self._client = client
        self._sleep = sleep

    def _genai(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(
                vertexai=True,
                project=self._settings.google_cloud_project,
                location=self._settings.google_cloud_location,
            )
        return self._client

    def _model(self, prompt: Prompt) -> str:
        return (
            self._settings.model_lite
            if prompt.model_env == "MODEL_LITE"
            else self._settings.model_fast
        )

    def version(self, task: str) -> tuple[str, str]:
        prompt = load_prompt(_TASKS[task])
        return self._model(prompt), prompt.ref

    async def _call[T: BaseModel](
        self, prompt: Prompt, parts: list[Any], schema: type[T]
    ) -> ReaderCall[T]:
        model = self._model(prompt)
        config = types.GenerateContentConfig(
            temperature=0,
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel(self._settings.reader_thinking_level.upper())
            ),
            response_mime_type="application/json",
            response_schema=schema,
        )
        last: Exception | None = None
        attempts = max(1, self._settings.reader_attempts)
        throttled = 0
        attempt = 0
        while attempt < attempts:
            started = time.monotonic()
            try:
                response = await asyncio.wait_for(
                    self._genai().aio.models.generate_content(
                        model=model, contents=[prompt.text, *parts], config=config
                    ),
                    timeout=self._settings.reader_timeout_seconds,
                )
                parsed = response.parsed
                value = parsed if isinstance(parsed, schema) else schema.model_validate(parsed)
                usage = response.usage_metadata
                return ReaderCall(
                    value=value,
                    model=model,
                    prompt_version=prompt.ref,
                    tokens_in=(usage.prompt_token_count or 0) if usage else 0,
                    tokens_out=(usage.candidates_token_count or 0) if usage else 0,
                    seconds=time.monotonic() - started,
                )
            except genai_errors.APIError as exc:
                # Rate limits and transient server errors wait and retry without using up an
                # attempt; anything else (a bad request, no access) fails at once.
                if (
                    exc.code not in _TRANSIENT
                    or throttled >= self._settings.reader_rate_limit_retries
                ):
                    raise ReaderFailed(f"{prompt.ref}: {exc.code} {exc.status}") from exc
                throttled += 1
                last = exc
                await self._sleep(_backoff(throttled))
                continue
            except (TimeoutError, ValueError) as exc:  # a slow call, or output failing the schema
                last = exc
            attempt += 1
        raise ReaderFailed(
            f"{prompt.ref} failed after {self._settings.reader_attempts} attempts"
        ) from last

    async def classify(self, image_png: bytes, text: str) -> ReaderCall[DocClassification]:
        prompt = load_prompt("classify_document")
        parts = [
            types.Part.from_bytes(data=image_png, mime_type="image/png"),
            f"PAGE 1 TEXT (untrusted document content):\n{text[:2000]}",
        ]
        return await self._call(prompt, parts, DocClassification)

    async def read_statement_page(
        self, image_png: bytes, chunks: str, *, page: int, context: str | None
    ) -> ReaderCall[StatementPageReading]:
        prompt = load_prompt("read_statement_page")
        parts: list[Any] = [
            f"This is page {page}." + (f" Context from page 1: {context}" if context else ""),
            types.Part.from_bytes(data=image_png, mime_type="image/png"),
            f"CHUNKS (untrusted document content):\n{chunks}",
        ]
        return await self._call(prompt, parts, StatementPageReading)

    async def read_invoice_page(
        self, image_png: bytes, chunks: str, *, page: int
    ) -> ReaderCall[InvoicePageReading]:
        return await self._call(
            load_prompt("read_invoice_page"),
            _page_parts(image_png, chunks, page),
            InvoicePageReading,
        )

    async def read_receipt_page(
        self, image_png: bytes, chunks: str, *, page: int
    ) -> ReaderCall[ReceiptPageReading]:
        return await self._call(
            load_prompt("read_receipt"), _page_parts(image_png, chunks, page), ReceiptPageReading
        )

    async def categorize(
        self, items: list[TransactionItem], vocabulary: str
    ) -> ReaderCall[CategorizeResult]:
        lines = "\n".join(item.model_dump_json() for item in items)
        parts: list[Any] = [
            f"CATEGORIES:\n{vocabulary}",
            f"LINES (untrusted bank statement content), one JSON object per line:\n{lines}",
        ]
        return await self._call(load_prompt("categorize_transactions"), parts, CategorizeResult)


def _page_parts(image_png: bytes, chunks: str, page: int) -> list[Any]:
    return [
        f"This is page {page}.",
        types.Part.from_bytes(data=image_png, mime_type="image/png"),
        f"CHUNKS (untrusted document content):\n{chunks or '(no text layer)'}",
    ]
