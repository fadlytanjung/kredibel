"""Order independence (spec 007, T007-05, AC-007-7; constitution non-negotiable 16): the same month
data in any order gives identical matches. Property-tested over permutations of a month that has
exact, ambiguous, grouped, split, net-of-tax and unrelated records, with a person's decisions."""

from datetime import date, timedelta
from decimal import Decimal as D
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from app.adapters.policy_files import load_reconciliation_policy
from app.domain.reconcile import Decisions, ManualMatch, assign_matches, match_key
from app.domain.reconcile_scoring import Kind, MatchRecord

POLICY = load_reconciliation_policy(Path(__file__).resolve().parents[3] / "contracts" / "policy")
DAY = date(2026, 3, 2)


def _bank(rid: str, amount: str, desc: str, days: int) -> MatchRecord:
    return MatchRecord(rid, "BANK", D(amount), DAY + timedelta(days=days), "MYR", description=desc)


def _inv(rid: str, kind: Kind, total: str, party: str, ref: str, days: int) -> MatchRecord:
    issued = DAY + timedelta(days=days)
    return MatchRecord(
        rid,
        kind,
        D(total),
        issued,
        "MYR",
        party=party,
        reference=ref,
        due_date=issued + timedelta(days=14),
    )


LEFT = [
    _bank("b01", "1000", "TRANSFER DAYBREAK CAFE INV-12", 3),
    _bank("b02", "500", "TRANSFER SPICE ROUTE", 4),
    _bank("b03", "1500", "TRANSFER HIGHLAND RESORT INV-3 INV-4", 5),
    _bank("b04", "600", "TRANSFER HARBOURVIEW HOTEL INV-7", 6),
    _bank("b05", "400", "TRANSFER HARBOURVIEW HOTEL INV-7", 9),
    _bank("b06", "985", "TRANSFER MORNING BAKES INV-20", 10),
    _bank("b07", "-250", "TRANSFER OUT PRIMEPACK PACKAGING", 11),
    _bank("b08", "77", "CASH DEPOSIT", 12),
    _bank("b09", "500", "TRANSFER SPICE ROUTE", 13),
]
RIGHT = [
    _inv("i12", "SALES_INVOICE", "1000", "Daybreak Café", "INV-12", 0),
    _inv("i01", "SALES_INVOICE", "500", "Spice Route", "INV-1", 1),
    _inv("i02", "SALES_INVOICE", "500", "Spice Route", "INV-2", 2),
    _inv("i03", "SALES_INVOICE", "1000", "Highland Resort", "INV-3", 0),
    _inv("i04", "SALES_INVOICE", "500", "Highland Resort", "INV-4", 1),
    _inv("i07", "SALES_INVOICE", "1000", "Harbourview Hotel", "INV-7", 2),
    _inv("i20", "SALES_INVOICE", "1000", "Morning Bakes", "INV-20", 3),
    _inv("p01", "PURCHASE_INVOICE", "250", "PrimePack Packaging", "PP-881", 4),
]
DECISIONS = Decisions(
    manual=(ManualMatch(("b08",), ("p01",)),),  # a person's (odd) choice stays whatever the order
    rejected=frozenset({match_key(("b02",), ("i01",))}),
)
BASELINE = assign_matches(LEFT, RIGHT, POLICY, workspace_currency="MYR", decisions=DECISIONS)


def test_the_baseline_month_has_every_kind_of_outcome():
    reasons = {r for m in BASELINE for r in m.reasons}
    statuses = {(m.status, m.method) for m in BASELINE}
    assert {"GROUPED", "SPLIT", "NET_OF_TAX"} <= reasons
    assert {("CONFIRMED", "AUTO"), ("CONFIRMED", "MANUAL"), ("PROPOSED", None)} <= statuses


@settings(max_examples=150, deadline=None)
@given(st.permutations(LEFT), st.permutations(RIGHT))
def test_any_upload_order_gives_the_same_matches(left, right):
    assert (
        assign_matches(left, right, POLICY, workspace_currency="MYR", decisions=DECISIONS)
        == BASELINE
    )
