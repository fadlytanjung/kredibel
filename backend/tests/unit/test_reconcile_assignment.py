"""Assignment of scored candidates (spec 007, T007-04, AC-007-3…6, AC-007-18); synthetic inputs.

Greedy by score, then date, then ID; single, grouped (one bank row, several invoices) and split
(several bank rows, one invoice) allocations compete; only a unique, review-free best is AUTO.
"""

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal as D
from pathlib import Path

import pytest

from app.adapters.policy_files import load_reconciliation_policy
from app.domain.reconcile import Decisions, ManualMatch, assign_matches, match_key
from app.domain.reconcile_scoring import MatchRecord

POLICY_DIR = Path(__file__).resolve().parents[3] / "contracts" / "policy"
DAY = date(2026, 3, 10)


@pytest.fixture
def policy():
    return load_reconciliation_policy(POLICY_DIR)


def bank(
    rid: str, amount: str, desc: str, day: date = DAY, party: str | None = None
) -> MatchRecord:
    return MatchRecord(rid, "BANK", D(amount), day, "MYR", party=party, description=desc)


def sales(rid: str, total: str, party: str, ref: str, day: date = DAY) -> MatchRecord:
    return MatchRecord(
        rid,
        "SALES_INVOICE",
        D(total),
        day,
        "MYR",
        party=party,
        reference=ref,
        due_date=day + timedelta(days=14),
    )


def _run(policy, left, right, decisions=None):
    return assign_matches(
        left, right, policy, workspace_currency="MYR", decisions=decisions or Decisions()
    )


def test_a_unique_strong_candidate_is_confirmed_automatically_with_reasons(policy):
    [m] = _run(
        policy,
        [bank("b1", "1000", "TRANSFER DAYBREAK CAFE INV-12")],
        [sales("i1", "1000", "Daybreak Café", "INV-12")],
    )
    assert (m.status, m.method, m.left_ids, m.right_ids) == ("CONFIRMED", "AUTO", ("b1",), ("i1",))
    assert m.reasons == ("AMOUNT_EXACT", "PARTY_MATCH", "REFERENCE_IN_TEXT", "DATE_NEAR")
    assert m.match_id == match_key(("b1",), ("i1",)) and m.match_id.startswith("mat_")


def test_two_equal_invoices_are_only_proposed_with_both_candidates(policy):
    left = [bank("b1", "500", "TRANSFER SPICE ROUTE")]
    right = [sales("i1", "500", "Spice Route", "INV-1"), sales("i2", "500", "Spice Route", "INV-2")]
    [m] = _run(policy, left, right)
    assert m.status == "PROPOSED" and m.method is None
    assert set(m.alternatives) == {match_key(("b1",), ("i1",)), match_key(("b1",), ("i2",))} - {
        m.match_id
    }


def test_a_conflicting_value_or_a_possible_tax_shortfall_is_never_automatic(policy):
    conflicted = replace(bank("b1", "1000", "TRANSFER DAYBREAK CAFE INV-12"), has_conflict=True)
    [m] = _run(policy, [conflicted], [sales("i1", "1000", "Daybreak Café", "INV-12")])
    assert m.status == "PROPOSED" and m.requires_review
    [m] = _run(
        policy,
        [bank("b1", "985", "TRANSFER DAYBREAK CAFE INV-12")],
        [sales("i1", "1000", "Daybreak Café", "INV-12")],
    )
    assert m.status == "PROPOSED" and "NET_OF_TAX" in m.reasons


def test_amount_and_date_alone_are_proposed_not_confirmed(policy):
    left = [bank("b1", "1000", "INSTANT TRANSFER 77812")]
    [m] = _run(policy, left, [sales("i1", "1000", "Daybreak Café", "INV-12")])
    assert m.status == "PROPOSED" and m.reasons == ("AMOUNT_EXACT", "DATE_NEAR")
    assert policy.thresholds.propose_score <= m.score < policy.thresholds.auto_confirm_score


def test_one_payment_for_several_invoices_is_a_grouped_match(policy):
    left = [bank("b1", "1500", "TRANSFER HIGHLAND RESORT INV-3 INV-4")]
    right = [
        sales("i3", "1000", "Highland Resort", "INV-3"),
        sales("i4", "500", "Highland Resort", "INV-4"),
    ]
    [m] = _run(policy, left, right)
    assert (m.status, m.method, m.left_ids, m.right_ids) == (
        "CONFIRMED",
        "AUTO",
        ("b1",),
        ("i3", "i4"),
    )
    assert "GROUPED" in m.reasons and m.amount_difference == D(0)


def test_several_payments_for_one_invoice_are_a_split_match(policy):
    left = [
        bank("b1", "600", "TRANSFER HIGHLAND RESORT INV-5"),
        bank("b2", "400", "TRANSFER HIGHLAND RESORT INV-5", DAY + timedelta(days=5)),
    ]
    [m] = _run(policy, left, [sales("i5", "1000", "Highland Resort", "INV-5")])
    assert (m.status, m.left_ids, m.right_ids) == ("CONFIRMED", ("b1", "b2"), ("i5",))
    assert "SPLIT" in m.reasons


def test_a_group_competes_with_a_single_match_before_assignment(policy):
    left = [bank("b1", "1000", "TRANSFER HIGHLAND RESORT")]
    right = [
        sales("i1", "1000", "Highland Resort", "INV-1"),
        sales("i2", "600", "Highland Resort", "INV-2"),
        sales("i3", "400", "Highland Resort", "INV-3"),
    ]
    [m] = _run(policy, left, right)
    assert m.status == "PROPOSED"  # the single and the pair explain the same payment equally well
    assert len(m.alternatives) >= 1


def test_no_record_is_used_twice(policy):
    left = [
        bank("b1", "1000", "TRANSFER DAYBREAK CAFE INV-12"),
        bank("b2", "1000", "TRANSFER DAYBREAK CAFE INV-12"),
    ]
    matches = _run(policy, left, [sales("i1", "1000", "Daybreak Café", "INV-12")])
    used = [rid for m in matches for rid in (*m.left_ids, *m.right_ids)]
    assert len(used) == len(set(used)) and len(matches) == 1 and matches[0].status == "PROPOSED"


def test_a_rejected_proposal_never_returns(policy):
    left = [bank("b1", "500", "TRANSFER SPICE ROUTE")]
    right = [sales("i1", "500", "Spice Route", "INV-1"), sales("i2", "500", "Spice Route", "INV-2")]
    first = _run(policy, left, right)[0]
    again = _run(policy, left, right, Decisions(rejected=frozenset({first.match_id})))
    assert all(m.match_id != first.match_id for m in again)
    assert [m.right_ids for m in again] == [tuple(set(("i1", "i2")) - set(first.right_ids))]


def test_a_manual_match_is_kept_and_its_records_are_not_offered_again(policy):
    left = [bank("b1", "1000", "TRANSFER DAYBREAK CAFE INV-12"), bank("b2", "1000", "CASH DEPOSIT")]
    right = [sales("i1", "1000", "Daybreak Café", "INV-12")]
    decisions = Decisions(manual=(ManualMatch(("b2",), ("i1",)),))
    [m] = _run(policy, left, right, decisions)
    assert (m.status, m.method, m.left_ids, m.right_ids) == (
        "CONFIRMED",
        "MANUAL",
        ("b2",),
        ("i1",),
    )


def test_the_same_inputs_in_any_order_give_the_same_matches(policy):
    left = [
        bank("b1", "1500", "TRANSFER HIGHLAND RESORT INV-3 INV-4"),
        bank("b2", "500", "TRANSFER SPICE ROUTE"),
        bank("b3", "1000", "TRANSFER DAYBREAK CAFE INV-12"),
    ]
    right = [
        sales("i3", "1000", "Highland Resort", "INV-3"),
        sales("i4", "500", "Highland Resort", "INV-4"),
        sales("i1", "500", "Spice Route", "INV-1"),
        sales("i12", "1000", "Daybreak Café", "INV-12"),
    ]
    assert _run(policy, left, right) == _run(policy, list(reversed(left)), list(reversed(right)))
