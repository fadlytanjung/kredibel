"""The month run asks the model to rank a proposal's candidates (spec 023, AC-023-7), keeps the
ranking while the candidates stay the same, and never ranks a proposal without rivals. Synthetic."""

from datetime import date
from decimal import Decimal as D
from types import SimpleNamespace

from app.agents.nodes.month_nodes import rank_proposals
from app.domain.review_items import ReviewCandidate, ReviewItem, ReviewSubject, ReviewSuggestion
from tests.fakes.document_reader import FakeDocumentReader
from tests.fakes.review_item_repository import FakeReviewItemRepository


def _item(item_id: str, ids: list[str]) -> ReviewItem:
    return ReviewItem(
        item_id=item_id,
        kind="PROPOSED_MATCH",
        month="2026-05",
        doc_id=None,
        title="Confirm the payment",
        status="OPEN",
        priority=70,
        allowed_actions=["CONFIRM_MATCH", "MATCH", "REJECT_MATCH"],
        subject=ReviewSubject(bank_line_ids=["tx_1"], match_id=ids[0]),
        suggestion=ReviewSuggestion(
            candidates=[
                ReviewCandidate(match_id=i, bank_line_ids=["tx_1"], score=D("0.8")) for i in ids
            ]
        ),
    )


def _result():
    line = SimpleNamespace(
        tx_id="tx_1", date=date(2026, 5, 6), description="TRF JAYA TEKNIK", amount=D("-100")
    )
    return SimpleNamespace(data=SimpleNamespace(all_lines=[line], invoices=[], receipts=[]))


async def test_ac023_7_a_proposal_with_rivals_is_ranked_once_and_kept_while_unchanged():
    reader, items = FakeDocumentReader(), FakeReviewItemRepository()
    deps = SimpleNamespace(reader=reader, review_items=items)
    fresh = [_item("itm_1", ["mat_a", "mat_b"]), _item("itm_2", ["mat_c"])]

    ranked = await rank_proposals(deps, "org_1", "2026-05", fresh, _result())  # type: ignore[arg-type]
    first = ranked[0].suggestion
    assert [(c.match_id, c.ai_rank) for c in first.candidates] == [("mat_a", 2), ("mat_b", 1)]
    assert first.ranked_by == "fake-model@rank_candidates@test"
    assert ranked[1].suggestion.ranked_by is None, "no rivals, nothing to rank"

    await items.replace_month_review_items("org_1", "2026-05", ranked, now=None)  # type: ignore[arg-type]
    again = await rank_proposals(deps, "org_1", "2026-05", fresh, _result())  # type: ignore[arg-type]
    assert [c.ai_rank for c in again[0].suggestion.candidates] == [2, 1]
    assert [name for name, _ in reader.calls].count("rank_candidates") == 1, "kept, not asked again"
