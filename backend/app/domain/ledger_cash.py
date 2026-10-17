"""Bank lines against their bookings on the ledger's bank account (docs/08 §6.2, ledger cash). Pure.

Matching against documents comes first. A line no document explains may then be matched to the
ledger entry that books it: the account the person mapped the bank account to, the same amount
(no adjustment), within `ledgerDays`. It is automatic only when the pair is unique both ways (no
other line or booking of that amount on the account within `rivalDays`), neither side's readings
conflict, and the booking's words name the line or its reference is printed on it. Anything less
stays unmatched for a person, as before.
"""

from app.domain.reconcile import Allocation, match_key
from app.domain.reconcile_scoring import MatchRecord, score_pair
from app.domain.reconciliation_policy import ReconciliationPolicy

BOOKED = "LEDGER_BOOKED"


def _same(a: MatchRecord, b: MatchRecord, policy: ReconciliationPolicy, currency: str) -> bool:
    """Same account, same direction and the same amount within tolerance; dates are not compared."""
    if a.amount is None or b.amount is None or a.held or b.held:
        return False
    if a.account_id is None or a.account_id != b.account_id or a.amount * b.amount <= 0:
        return False
    tolerance = policy.tolerance(max(abs(a.amount), abs(b.amount)), currency)
    return tolerance is not None and abs(abs(a.amount) - abs(b.amount)) <= tolerance


def _near(a: MatchRecord, b: MatchRecord, days: int) -> bool:
    return a.date is not None and b.date is not None and abs((a.date - b.date).days) <= days


def match_ledger_cash(
    lines: list[MatchRecord],
    bookings: list[MatchRecord],
    policy: ReconciliationPolicy,
    *,
    workspace_currency: str,
    taken: frozenset[str] = frozenset(),
    rejected: frozenset[str] = frozenset(),
) -> list[Allocation]:
    """Automatic bank-to-ledger matches for the lines not in `taken` (already matched or proposed
    with documents, or matched by a person); rejected match IDs never return."""
    rival_days = policy.ledger_cash.rival_days
    out: list[Allocation] = []
    for line in sorted(lines, key=lambda r: r.record_id):
        if line.record_id in taken:
            continue
        near = [b for b in bookings if _same(line, b, policy, workspace_currency)]
        near = [b for b in near if _near(line, b, rival_days)]
        if len(near) != 1:
            continue
        [booking] = near
        others = [ln for ln in lines if _same(ln, booking, policy, workspace_currency)]
        if [ln.record_id for ln in others if _near(ln, booking, rival_days)] != [line.record_id]:
            continue
        scored = score_pair(line, booking, policy, workspace_currency=workspace_currency)
        if scored is None or scored.reasons[0] != "AMOUNT_EXACT" or scored.requires_review:
            continue
        if scored.party < policy.ledger_cash.min_party and not scored.reference:
            continue
        match_id = match_key((line.record_id,), (booking.record_id,))
        if match_id in rejected:
            continue
        out.append(
            Allocation(
                match_id=match_id,
                left_ids=(line.record_id,),
                right_ids=(booking.record_id,),
                status="CONFIRMED",
                method="AUTO",
                score=scored.score,
                reasons=(*scored.reasons, BOOKED),
                amount_difference=scored.amount_difference,
                requires_review=False,
            )
        )
    return sorted(out, key=lambda a: a.match_id)
