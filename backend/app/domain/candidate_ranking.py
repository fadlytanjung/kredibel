"""The model's view of a proposal's candidates (spec 023, AC-023-7). Pure.

Code finds and scores every candidate and decides what is automatic; for a proposal with rivals the
model only orders the candidates code found and says why in one sentence, for the person deciding.
"""

from dataclasses import replace

from pydantic import BaseModel, Field

from app.domain.review_items import ReviewCandidate

MAX_REASON = 240


class RankedCandidate(BaseModel):
    match_id: str
    reason: str = ""


class CandidateRanking(BaseModel):
    order: list[RankedCandidate] = Field(default_factory=list)


def apply_ranking(
    candidates: list[ReviewCandidate], ranking: CandidateRanking
) -> list[ReviewCandidate]:
    """Ranks only the candidates code found, in the model's order (an ID it invents is ignored);
    the candidates keep their order and scores."""
    known = {c.match_id for c in candidates}
    order: list[tuple[str, str]] = []
    for item in ranking.order:
        if item.match_id in known and item.match_id not in {m for m, _ in order}:
            order.append((item.match_id, " ".join(item.reason.split())[:MAX_REASON]))
    rank = {match_id: (n, reason) for n, (match_id, reason) in enumerate(order, start=1)}
    return [
        replace(c, ai_rank=rank[c.match_id][0], ai_reason=rank[c.match_id][1] or None)
        if c.match_id in rank
        else c
        for c in candidates
    ]
