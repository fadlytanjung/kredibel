"""DocumentReader on Gemini (docs/07 §4–§5, ADR-023): the instruction, the page image and the page's
chunks are separate content parts; the document never sits inside the instruction (docs/06 §6)."""

import asyncio
import time
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.adapters.prompt_files import Prompt, load_prompt
from app.core.settings import Settings
from app.domain.reading import DocClassification, StatementPageReading
from app.ports.document_reader import DocumentReader, ReaderCall

_TASKS = {"classify": "classify_document", "statement_page": "read_statement_page"}


class ReaderFailed(Exception):
    pass


class GeminiDocumentReader(DocumentReader):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: genai.Client | None = None

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
        for _ in range(max(1, self._settings.reader_attempts)):
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
            except (
                TimeoutError,
                ValueError,
            ) as exc:  # a slow call, or output that fails the schema
                last = exc
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
