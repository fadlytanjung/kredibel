"""The AI reader (docs/07 §4–§5, ADR-023): classifies a document and extracts a page from its image
plus its layout chunks. Implemented with Gemini; tests use a recorded fake."""

from dataclasses import dataclass
from typing import Any, Protocol

from app.domain.reading import (
    CategorizeResult,
    DocClassification,
    InvoicePageReading,
    ReceiptPageReading,
    StatementPageReading,
    TransactionItem,
)


@dataclass(frozen=True)
class ReaderCall[T]:
    value: T
    model: str
    prompt_version: str
    tokens_in: int = 0
    tokens_out: int = 0
    seconds: float = 0.0


class DocumentReader(Protocol):
    def version(self, task: str) -> tuple[str, str]:
        """(model, prompt version) a task runs with; part of the extraction cache key."""
        ...

    async def classify(self, image_png: bytes, text: str) -> ReaderCall[DocClassification]:
        """The document type from page 1's image and up to 2,000 characters of its text."""
        ...

    async def read_statement_page(
        self, image_png: bytes, chunks: str, *, page: int, context: str | None
    ) -> ReaderCall[StatementPageReading]:
        """One statement page from its image and numbered chunks; `context` is page 1's header."""
        ...

    async def read_invoice_page(
        self, image_png: bytes, chunks: str, *, page: int
    ) -> ReaderCall[InvoicePageReading]:
        """One invoice page; each carries its own invoice number, so pages read independently."""
        ...

    async def read_receipt_page(
        self, image_png: bytes, chunks: str, *, page: int
    ) -> ReaderCall[ReceiptPageReading]:
        """One receipt page or photo; `chunks` is empty for a photo without a text layer."""
        ...

    async def categorize(
        self, items: list[TransactionItem], vocabulary: str
    ) -> ReaderCall[CategorizeResult]:
        """Categories for up to 100 bank lines the keyword rules left (docs/08 §4.1)."""
        ...

    async def explain_month(
        self,
        level: str,
        findings_facts: str,
        figures_summary: str,
        catalog_steps: list[str],
        retry_problems: list[str] | None = None,
    ) -> ReaderCall[Any]:
        """Gemini explanation for the month's fraud risk level (spec 008, AC-008-4)."""
        ...
