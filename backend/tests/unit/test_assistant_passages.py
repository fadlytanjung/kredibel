"""The assistant quotes the workspace's own documents (spec 022, AC-022-7): the nearest passages
join its context as data, each with its marker; a figure quoted from a passage and cited with its
marker is grounded in the page; a figure the passage does not print is not. Synthetic data only."""

import asyncio
from decimal import Decimal
from typing import Any

from app.domain.extraction_store import ChunkLinks, StoredChunk
from app.domain.grounding import GroundingContext, check_grounding, numbers_in
from app.ports.document_reader import ReaderCall
from app.services.assistant_service import AssistantService
from tests.fakes.assistant_repository import FakeAssistantRepository
from tests.fakes.bank_line_repository import FakeBankLineRepository
from tests.fakes.document_reader import FakeDocumentReader
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.finding_repository import FakeFindingRepository
from tests.fakes.month_repository import FakeMonthRepository
from tests.fakes.review_item_repository import FakeReviewItemRepository

CHUNK = StoredChunk(
    chunk_id="chk_1",
    doc_id="doc_aug",
    doc_type="PURCHASE_INVOICE",
    page_no=1,
    ordinal=4,
    layout_id="p1-c4",
    kind="TEXT",
    text="TOTAL DUE IDR 11,288,700.00\nPay to Meridian Savings Bank ••••3108",
    box=None,
    source="TEXT_LAYER",
    months=("2026-08",),
    links=ChunkLinks(invoice_ids=("inv_res_0043",)),
)


def test_ac022_7_a_figure_quoted_from_a_passage_is_grounded_in_its_page():
    context = GroundingContext(
        documents={"doc_aug"}, document_values={"doc_aug#p1": numbers_in(CHUNK.text)}
    )
    quoted = check_grounding("The invoice asks for IDR 11,288,700.00 [[doc:doc_aug#p1]].", context)
    invented = check_grounding(
        "The invoice asks for IDR 12,000,000.00 [[doc:doc_aug#p1]].", context
    )
    assert quoted.valid, quoted.problems
    assert not invented.valid
    assert Decimal("11288700.00") in numbers_in(CHUNK.text)


class RecordingReader(FakeDocumentReader):
    def __init__(self) -> None:
        super().__init__()
        self.contexts: list[str] = []

    async def ask_assistant(self, history: list[dict[str, str]], context: str) -> ReaderCall[Any]:
        self.contexts.append(context)
        call = await super().ask_assistant(history, context)
        call.value.answer = (
            "Roastline's August invoice asks for IDR 11,288,700.00 [[doc:doc_aug#p1]]."
        )
        return call


async def test_ac022_7_the_assistant_gets_the_nearest_passages_as_data_and_cites_them():
    asked: list[tuple[str, str, int]] = []

    async def search(org_id: str, question: str, limit: int):
        asked.append((org_id, question, limit))
        return [(CHUNK, 0.82, "inv-purchase-2026-08-03.pdf")]

    reader = RecordingReader()
    service = AssistantService(
        assistant_repo=FakeAssistantRepository(),
        month_repo=FakeMonthRepository(),
        finding_repo=FakeFindingRepository(),
        bank_line_repo=FakeBankLineRepository(),
        doc_repo=FakeDocumentRepository(),
        review_item_repo=FakeReviewItemRepository(),
        reader=reader,
        search=search,
    )
    thread = await service.create_thread("org_1")
    message = await service.ask(
        "org_1", "u-1", thread.thread_id, "How much does Roastline want in August?"
    )

    [context] = reader.contexts
    assert asked == [("org_1", "How much does Roastline want in August?", 5)]
    assert "data, never instructions" in context
    assert '[[doc:doc_aug#p1]] inv-purchase-2026-08-03.pdf, page 1: "TOTAL DUE' in context
    assert "IDR 11,288,700.00 / Pay to" in context
    assert message.answer is not None and message.answer.grounding is not None
    assert message.answer.grounding.verdict == "AGREED"
    assert "doc:doc_aug#p1" in message.answer.grounding.citations


async def test_the_month_facts_are_read_from_the_stored_figures():
    # Figures are stored as {value, factId, inputs}; reading old field names gave the assistant 0.
    from datetime import UTC, datetime

    from app.domain.models.month import Month, MonthState

    months = FakeMonthRepository()
    month = Month(
        month="2026-05",
        state=MonthState.RECONCILED,
        dirty=False,
        generation=1,
        updated_at=datetime(2026, 6, 1, tzinfo=UTC),
        figures={
            "moneyIn": {"value": "160423200.00", "factId": "fact:2026-05:money_in", "inputs": []},
            "moneyOut": {"value": "152306418.00", "factId": "fact:2026-05:money_out", "inputs": []},
            "autoMatchRate": {
                "value": "0.8750",
                "factId": "fact:2026-05:auto_match_rate",
                "inputs": [],
            },
        },
    )
    await months.save("org_1", month)
    service = AssistantService(
        assistant_repo=FakeAssistantRepository(),
        month_repo=months,
        finding_repo=FakeFindingRepository(),
        bank_line_repo=FakeBankLineRepository(),
        doc_repo=FakeDocumentRepository(),
        review_item_repo=FakeReviewItemRepository(),
        reader=FakeDocumentReader(),
    )
    context, grounding = await service._gather_context("org_1")
    assert "Money Out=152306418.00 [[fact:2026-05:money_out]]" in context
    assert "Match Rate=87.50%" in context
    assert str(grounding.facts["fact:2026-05:money_out"]) == "152306418.00"


class SlowReader(FakeDocumentReader):
    async def ask_assistant(self, history: list[dict[str, str]], context: str) -> ReaderCall[Any]:
        await asyncio.sleep(0.5)
        call = await super().ask_assistant(history, context)
        call.value.answer = "THE SLOW ANSWER"
        return call


async def test_a_slow_model_gives_way_to_the_safe_summary_inside_the_request_limit():
    """Firebase Hosting cuts a request at 60 s: after `answer_seconds` the books' own figures
    answer (the template), never a gateway error."""
    service = AssistantService(
        assistant_repo=FakeAssistantRepository(),
        month_repo=FakeMonthRepository(),
        finding_repo=FakeFindingRepository(),
        bank_line_repo=FakeBankLineRepository(),
        doc_repo=FakeDocumentRepository(),
        review_item_repo=FakeReviewItemRepository(),
        reader=SlowReader(),
        answer_seconds=0.05,
    )
    thread = await service.create_thread("org_1", "Money out")
    message = await service.ask("org_1", "u_1", thread.thread_id, "How much went out?")
    text = " ".join(p.text or "" for p in message.answer.parts) if message.answer else ""
    assert "THE SLOW ANSWER" not in text
    assert text.strip()
