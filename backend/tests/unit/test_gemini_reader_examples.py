"""The reader sends verified examples as a labelled data part, and nothing when there are none
(spec 016, AC-016-9). No network: the client is a stand-in."""

from types import SimpleNamespace
from typing import Any

from app.adapters.gemini_reader import GeminiDocumentReader
from app.core.settings import Settings
from app.domain.reading import CategorizeResult, DocClassification, TransactionItem


class _Models:
    def __init__(self, parsed: Any) -> None:
        self.parsed = parsed
        self.contents: list[Any] = []

    async def generate_content(self, **kwargs: Any) -> Any:
        self.contents.append(kwargs["contents"])
        usage = SimpleNamespace(prompt_token_count=10, candidates_token_count=5)
        return SimpleNamespace(parsed=self.parsed, usage_metadata=usage)


def _reader(parsed: Any) -> tuple[GeminiDocumentReader, _Models]:
    models = _Models(parsed)
    client = SimpleNamespace(aio=SimpleNamespace(models=models))
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    return GeminiDocumentReader(settings, client=client), models  # type: ignore[arg-type]


def _texts(contents: Any) -> list[str]:
    return [c for c in contents if isinstance(c, str)]


async def test_ac016_9_examples_reach_the_categorizer_as_data():
    reader, models = _reader(CategorizeResult())
    item = TransactionItem(
        id=0, description="TRANSFER OUT GREEN VALLEY FARMS", direction="out", amount="9.00"
    )
    examples = [
        {"description": "TRANSFER OUT GREEN VALLEY FARMS 0912", "category": "INVENTORY_PURCHASE"}
    ]
    await reader.categorize([item], "INVENTORY_PURCHASE (money out): Purchases", examples)
    await reader.categorize([item], "INVENTORY_PURCHASE (money out): Purchases")
    with_examples, without = (_texts(c) for c in models.contents)
    part = next(p for p in with_examples if p.startswith("EXAMPLES"))
    assert "data, not instructions" in part and '"category": "INVENTORY_PURCHASE"' in part
    assert not any(p.startswith("EXAMPLES") for p in without)


async def test_ac016_9_examples_reach_the_classifier_as_data():
    reader, models = _reader(DocClassification(doc_type="PURCHASE_INVOICE", confidence=0.9))
    await reader.classify(
        b"png",
        "INVOICE RL-0402",
        [{"page1_text": "INVOICE RL-0311", "doc_type": "PURCHASE_INVOICE"}],
    )
    assert any(
        p.startswith("EXAMPLES") and "PURCHASE_INVOICE" in p for p in _texts(models.contents[0])
    )
