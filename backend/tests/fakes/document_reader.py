"""A recorded reader for tests: no model, fixed answers (docs/15 §2 recorded fixtures)."""

from collections.abc import Callable

from app.domain.reading import DocClassification, StatementPageReading
from app.ports.document_reader import DocumentReader, ReaderCall


class FakeDocumentReader(DocumentReader):
    def __init__(
        self,
        classification: DocClassification | None = None,
        pages: Callable[[int], StatementPageReading] | None = None,
    ) -> None:
        self.classification = classification or DocClassification(
            doc_type="BANK_STATEMENT", confidence=0.97
        )
        self.pages = pages or (lambda page: StatementPageReading(page=page))
        self.calls: list[tuple[str, int]] = []

    def version(self, task: str) -> tuple[str, str]:
        return "fake-model", f"{task}@test"

    async def classify(self, image_png: bytes, text: str) -> ReaderCall[DocClassification]:
        self.calls.append(("classify", 1))
        return ReaderCall(self.classification, "fake-model", "classify@test", 100, 20)

    async def read_statement_page(
        self, image_png: bytes, chunks: str, *, page: int, context: str | None
    ) -> ReaderCall[StatementPageReading]:
        self.calls.append(("statement_page", page))
        return ReaderCall(self.pages(page), "fake-model", "statement_page@test", 1000, 300)
