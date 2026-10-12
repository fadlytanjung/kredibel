"""Deterministic assignment of scored candidates (docs/08 §6.3, ADR-025). Pure.

Single, grouped and split allocations are all scored first and compete; then greedily by score,
earlier date, then ID, each candidate whose records are still free becomes a match. Only a best
that is high enough, clearly ahead of every competitor and free of review flags is confirmed
automatically; the rest are proposals for a person. A person's decisions are inputs: manual matches
stay, rejected proposals never return.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from itertools import combinations
from typing import Literal

from app.core.ids import content_id

from .reconcile_scoring import CandidateScore, MatchRecord, score_group, score_pair
from .reconciliation_policy import ReconciliationPolicy


def match_key(left_ids: Iterable[str], right_ids: Iterable[str]) -> str:
    """The same records always give the same match ID, whatever the order they arrived in."""
    return content_id("mch", "|".join(sorted(left_ids)), "|".join(sorted(right_ids)))


@dataclass(frozen=True)
class ManualMatch:
    left_ids: tuple[str, ...]
    right_ids: tuple[str, ...]


@dataclass(frozen=True)
class Decisions:
    manual: tuple[ManualMatch, ...] = ()
    rejected: frozenset[str] = frozenset()  # match IDs a person rejected


@dataclass(frozen=True)
class Allocation:
    match_id: str
    left_ids: tuple[str, ...]
    right_ids: tuple[str, ...]
    status: Literal["CONFIRMED", "PROPOSED"]
    method: Literal["AUTO", "MANUAL"] | None
    score: Decimal
    reasons: tuple[str, ...]
    amount_difference: Decimal
    requires_review: bool
    alternatives: tuple[str, ...] = ()  # competing candidates a person can pick instead


@dataclass(frozen=True)
class _Candidate:
    match_id: str
    left_ids: tuple[str, ...]
    right_ids: tuple[str, ...]
    scored: CandidateScore
    first_date: date

    @property
    def records(self) -> frozenset[str]:
        return frozenset((*self.left_ids, *self.right_ids))


def _candidate(
    lefts: Sequence[MatchRecord], rights: Sequence[MatchRecord], scored: CandidateScore
) -> _Candidate:
    left_ids = tuple(sorted(r.record_id for r in lefts))
    right_ids = tuple(sorted(r.record_id for r in rights))
    first = min(r.date for r in (*lefts, *rights) if r.date is not None)
    return _Candidate(match_key(left_ids, right_ids), left_ids, right_ids, scored, first)


def _abs(record: MatchRecord) -> Decimal:
    return abs(record.amount) if record.amount is not None else Decimal(0)


def _candidates(
    left: Sequence[MatchRecord],
    right: Sequence[MatchRecord],
    policy: ReconciliationPolicy,
    currency: str,
) -> list[_Candidate]:
    out: list[_Candidate] = []
    singles: dict[tuple[str, str], CandidateScore] = {}
    for lo in left:
        for ro in right:
            if scored := score_pair(lo, ro, policy, workspace_currency=currency):
                singles[(lo.record_id, ro.record_id)] = scored
                out.append(_candidate((lo,), (ro,), scored))
    largest = policy.thresholds.max_split_parts
    # One payment, several documents: only documents smaller than the payment can be parts.
    for lo in left:
        parts = sorted((ro for ro in right if _abs(ro) < _abs(lo)), key=lambda r: r.record_id)
        for size in range(2, largest + 1):
            for group in combinations(parts, size):
                if scored := score_group((lo,), group, policy, workspace_currency=currency):
                    out.append(_candidate((lo,), group, scored))
    # Several payments, one document.
    for ro in right:
        parts = sorted((lo for lo in left if _abs(lo) < _abs(ro)), key=lambda r: r.record_id)
        for size in range(2, largest + 1):
            for group in combinations(parts, size):
                if scored := score_group(group, (ro,), policy, workspace_currency=currency):
                    out.append(_candidate(group, (ro,), scored))
    return out


def assign_matches(
    left: Sequence[MatchRecord],
    right: Sequence[MatchRecord],
    policy: ReconciliationPolicy,
    *,
    workspace_currency: str,
    decisions: Decisions,
) -> list[Allocation]:
    """Matches between two sides of one kind (bank ↔ documents, bank ↔ ledger cash, documents ↔
    ledger); within a call every record is used at most once."""
    by_id = {r.record_id: r for r in (*left, *right)}
    used: set[str] = set()
    out: list[Allocation] = []
    for manual in decisions.manual:
        ids = (*manual.left_ids, *manual.right_ids)
        if any(i not in by_id or i in used for i in ids):
            continue  # its records are gone (deleted, held): the decision waits for them
        used.update(ids)
        out.append(_manual(manual, by_id, policy, workspace_currency))

    pool = [
        c
        for c in _candidates(left, right, policy, workspace_currency)
        if c.match_id not in decisions.rejected and not (c.records & used)
    ]
    pool.sort(key=lambda c: (-c.scored.score, c.first_date, c.match_id))
    thresholds = policy.thresholds
    for best in pool:
        if best.records & used:
            continue
        if best.scored.score < thresholds.propose_score:
            break  # sorted by score: nothing further reaches a proposal
        rivals = [
            c
            for c in pool
            if c is not best and not (c.records & used) and (c.records & best.records)
        ]
        runner_up = max((c.scored.score for c in rivals), default=None)
        clear = runner_up is None or runner_up < best.scored.score - thresholds.ambiguity_margin
        auto = (
            best.scored.score >= thresholds.auto_confirm_score
            and clear
            and not best.scored.requires_review
        )
        used.update(best.records)
        out.append(
            Allocation(
                match_id=best.match_id,
                left_ids=best.left_ids,
                right_ids=best.right_ids,
                status="CONFIRMED" if auto else "PROPOSED",
                method="AUTO" if auto else None,
                score=best.scored.score,
                reasons=best.scored.reasons,
                amount_difference=best.scored.amount_difference,
                requires_review=best.scored.requires_review,
                alternatives=() if auto else tuple(sorted(c.match_id for c in rivals)),
            )
        )
    return sorted(out, key=lambda a: a.match_id)


def _manual(
    manual: ManualMatch,
    by_id: dict[str, MatchRecord],
    policy: ReconciliationPolicy,
    currency: str,
) -> Allocation:
    lefts = tuple(by_id[i] for i in sorted(manual.left_ids))
    rights = tuple(by_id[i] for i in sorted(manual.right_ids))
    scored = (
        score_pair(lefts[0], rights[0], policy, workspace_currency=currency)
        if len(lefts) == len(rights) == 1
        else score_group(lefts, rights, policy, workspace_currency=currency)
    )
    paid = sum((_abs(r) for r in lefts), Decimal(0))
    total = sum((_abs(r) for r in rights), Decimal(0))
    return Allocation(
        match_id=match_key(manual.left_ids, manual.right_ids),
        left_ids=tuple(r.record_id for r in lefts),
        right_ids=tuple(r.record_id for r in rights),
        status="CONFIRMED",
        method="MANUAL",
        score=scored.score if scored else Decimal(0),
        reasons=scored.reasons if scored else (),
        amount_difference=paid - total,
        requires_review=False,
    )
