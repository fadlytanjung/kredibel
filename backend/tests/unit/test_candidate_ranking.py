"""The model ranks a proposal's candidates (spec 023, AC-023-7): only the candidates code found are
ranked, in the model's order, each with its sentence; an ID the model invents is ignored and the
matching itself never changes. Synthetic data only."""

from decimal import Decimal as D

from app.domain.candidate_ranking import CandidateRanking, RankedCandidate, apply_ranking
from app.domain.review_items import ReviewCandidate


def _c(match_id: str, score: str) -> ReviewCandidate:
    return ReviewCandidate(
        match_id=match_id, bank_line_ids=["tx_1"], invoice_ids=[f"inv_{match_id}"], score=D(score)
    )


def test_ac023_7_the_models_order_and_reasons_land_on_the_candidates_code_found():
    candidates = [_c("mat_a", "0.80"), _c("mat_b", "0.78")]
    ranking = CandidateRanking(
        order=[
            RankedCandidate(
                match_id="mat_b", reason="The reference INV-12 is in the transfer text."
            ),
            RankedCandidate(match_id="mat_made_up", reason="Invented."),
            RankedCandidate(match_id="mat_a", reason="Same party, but a later invoice."),
        ]
    )
    ranked = apply_ranking(candidates, ranking)
    assert [(c.match_id, c.ai_rank) for c in ranked] == [("mat_a", 2), ("mat_b", 1)]
    assert ranked[1].ai_reason == "The reference INV-12 is in the transfer text."
    assert [c.score for c in ranked] == [D("0.80"), D("0.78")], "code's scores are untouched"


def test_ac023_7_an_empty_or_unknown_ranking_leaves_the_candidates_unranked():
    candidates = [_c("mat_a", "0.80"), _c("mat_b", "0.78")]
    ranked = apply_ranking(
        candidates, CandidateRanking(order=[RankedCandidate(match_id="x", reason="?")])
    )
    assert all(c.ai_rank is None and c.ai_reason is None for c in ranked)
