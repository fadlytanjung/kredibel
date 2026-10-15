"""A recorded reader for tests: no model, fixed answers (docs/15 §2 recorded fixtures)."""

from collections.abc import Callable
from typing import Any

from app.domain.reading import (
    CategorizeResult,
    CategoryChoice,
    DocClassification,
    InvoicePageReading,
    LedgerMappingProposal,
    ReceiptPageReading,
    StatementPageReading,
    TransactionItem,
)
from app.ports.document_reader import DocumentReader, ReaderCall


class FakeDocumentReader(DocumentReader):
    def __init__(
        self,
        classification: DocClassification | Callable[[str], DocClassification] | None = None,
        pages: Callable[[int], StatementPageReading] | None = None,
        invoice_pages: Callable[[int], InvoicePageReading] | None = None,
        receipt_pages: Callable[[int], ReceiptPageReading] | None = None,
        categories: Callable[[TransactionItem], tuple[str, float]] | None = None,
        month_explanation: Any | None = None,
        mapping: LedgerMappingProposal | Callable[[list[str]], LedgerMappingProposal] | None = None,
    ) -> None:
        self.mapping = mapping or LedgerMappingProposal()
        self.classification = classification or DocClassification(
            doc_type="BANK_STATEMENT", confidence=0.97
        )
        self.pages = pages or (lambda page: StatementPageReading(page=page))
        self.invoice_pages = invoice_pages or (lambda page: InvoicePageReading(page=page))
        self.receipt_pages = receipt_pages or (lambda page: ReceiptPageReading(page=page))
        self.categories = categories or (lambda item: ("UNKNOWN", 0.0))
        self.month_explanation = month_explanation
        self.calls: list[tuple[str, int]] = []

    def version(self, task: str) -> tuple[str, str]:
        return "fake-model", f"{task}@test"

    async def map_ledger_columns(
        self, header: list[str], shapes: list[list[str]]
    ) -> ReaderCall[LedgerMappingProposal]:
        self.calls.append(("map_ledger", len(header)))
        value = self.mapping(header) if callable(self.mapping) else self.mapping
        return ReaderCall(value, "fake-model", "map_ledger_columns@test", 80, 30)

    async def classify(self, image_png: bytes, text: str) -> ReaderCall[DocClassification]:
        self.calls.append(("classify", 1))
        value = self.classification(text) if callable(self.classification) else self.classification
        return ReaderCall(value, "fake-model", "classify@test", 100, 20)

    async def read_statement_page(
        self, image_png: bytes, chunks: str, *, page: int, context: str | None
    ) -> ReaderCall[StatementPageReading]:
        self.calls.append(("statement_page", page))
        return ReaderCall(self.pages(page), "fake-model", "statement_page@test", 1000, 300)

    async def read_invoice_page(
        self, image_png: bytes, chunks: str, *, page: int
    ) -> ReaderCall[InvoicePageReading]:
        self.calls.append(("invoice_page", page))
        return ReaderCall(self.invoice_pages(page), "fake-model", "invoice_page@test", 900, 250)

    async def read_receipt_page(
        self, image_png: bytes, chunks: str, *, page: int
    ) -> ReaderCall[ReceiptPageReading]:
        self.calls.append(("receipt_page", page))
        return ReaderCall(self.receipt_pages(page), "fake-model", "receipt_page@test", 600, 150)

    async def categorize(
        self, items: list[TransactionItem], vocabulary: str
    ) -> ReaderCall[CategorizeResult]:
        self.calls.append(("categorize", len(items)))
        choices = [
            CategoryChoice(id=item.id, category=cat, confidence=conf)
            for item in items
            for cat, conf in [self.categories(item)]
        ]
        return ReaderCall(CategorizeResult(items=choices), "fake-lite", "categorize@test", 500, 200)

    async def explain_month(
        self,
        level: str,
        findings_facts: str,
        figures_summary: str,
        catalog_steps: list[str],
        retry_problems: list[str] | None = None,
    ) -> ReaderCall[Any]:
        self.calls.append(("explain_month", len(catalog_steps)))
        if self.month_explanation is None:
            from app.domain.risk import MonthExplanation

            res = MonthExplanation(
                summary="Standard explanation for the month.",
                next_steps=catalog_steps,
            )
        elif callable(self.month_explanation):
            res = self.month_explanation(level, retry_problems)
        else:
            res = self.month_explanation
        return ReaderCall(res, "fake-model", "explain_month@test", 400, 150)

    async def suggest_match(
        self,
        bank_line_info: str,
        candidates_info: str,
    ) -> ReaderCall[Any]:
        from app.domain.models.assistant import MatchSuggestion

        self.calls.append(("suggest_match", 1))
        return ReaderCall(
            MatchSuggestion(
                recommended_doc_id=None,
                confidence=0.85,
                reason="Semantic match based on counterparty and amount.",
                missing_document_advice="Check for invoice or receipt.",
            ),
            "fake-model",
            "suggest_match@test",
            200,
            100,
        )

    async def ask_assistant(
        self,
        history: list[dict[str, str]],
        context: str,
    ) -> ReaderCall[Any]:
        from pydantic import BaseModel, Field

        class FakeAssistantResponse(BaseModel):
            answer: str
            suggested_followups: list[str] = Field(default_factory=list)

        self.calls.append(("ask_assistant", len(history)))
        return ReaderCall(
            FakeAssistantResponse(
                answer=(
                    "Here is the financial summary based on your books: "
                    "[[fact:2026-05:money_in]] is verified."
                ),
                suggested_followups=[
                    "Why is May risk level Medium?",
                    "Show unmatched bank lines",
                ],
            ),
            "fake-model",
            "assistant@test",
            300,
            150,
        )
