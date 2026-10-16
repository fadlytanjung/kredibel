"""Bank lines against the ledger's bank account (docs/08 §6.2, ledger cash): a line no document
explains is matched automatically to the one ledger entry on its mapped account with the same amount
within the window, when no other line or entry of that amount is near and the booking's words name
the line. Anything less stays for a person. Synthetic data only."""

from datetime import date, timedelta
from decimal import Decimal as D
from pathlib import Path

from app.adapters.policy_files import load_reconciliation_policy
from app.domain.ledger_cash import match_ledger_cash
from app.domain.reconcile import match_key
from app.domain.reconcile_scoring import MatchRecord

POLICY = load_reconciliation_policy(Path(__file__).resolve().parents[3] / "contracts" / "policy")
ACB = "ACB ••7712"
DAY = date(2026, 8, 4)


def bank(tx: str, amount: str, description: str, day: date = DAY, **kw) -> MatchRecord:
    return MatchRecord(
        tx, "BANK", D(amount), day, "IDR", description=description, account_id=ACB, **kw
    )


def entry(
    entry_id: str, amount: str, description: str, day: date = DAY, *, reference=None, accounts=()
) -> MatchRecord:
    return MatchRecord(
        entry_id,
        "LEDGER_CASH",
        D(amount),
        day,
        "IDR",
        party=description,
        reference=reference,
        account_id=ACB,
        aliases=tuple(accounts),
    )


def run(left, right, *, taken=frozenset(), rejected=frozenset()):
    return match_ledger_cash(
        left, right, POLICY, workspace_currency="IDR", taken=taken, rejected=rejected
    )


def test_a_unique_booking_that_names_the_line_is_matched_automatically():
    lines = [
        bank("st#1", "2500000", "CASH DEPOSIT REF 26080417682"),
        bank("st#2", "-8450000", "LOAN INSTALLMENT LN-0071-2291 REF 2608", DAY + timedelta(days=1)),
        bank("st#3", "-15000000", "WAREHOUSE RENT AUG REF 26080172706"),
    ]
    entries = [
        entry("le#1", "2500000", "Cash sales deposit", DAY + timedelta(days=2)),
        entry(
            "le#2",
            "-8450000",
            "Loan installment August 2026",
            DAY + timedelta(days=2),
            reference="LN-0071-2291",
        ),
        entry("le#3", "-15000000", "Rent", accounts=["Warehouse rent"]),
    ]

    found = {a.left_ids: a for a in run(lines, entries)}

    assert set(found) == {("st#1",), ("st#2",), ("st#3",)}
    for a in found.values():
        assert (a.status, a.method, a.requires_review) == ("CONFIRMED", "AUTO", False)
        assert a.match_id == match_key(a.left_ids, a.right_ids)
        assert a.reasons[0] == "AMOUNT_EXACT" and "LEDGER_BOOKED" in a.reasons
    assert (
        found[("st#2",)].right_ids == ("le#2",) and "REFERENCE_IN_TEXT" in found[("st#2",)].reasons
    )
    assert found[("st#3",)].right_ids == ("le#3",)  # the counter-account names the line


def test_rivals_conflicts_strangers_and_other_accounts_stay_for_a_person():
    lines = [
        # Two deposits of the same amount three days apart: either entry could book either.
        bank("st#1", "1750000", "CASH DEPOSIT REF 1", DAY),
        bank("st#2", "1750000", "CASH DEPOSIT REF 2", DAY + timedelta(days=3)),
        # The readers disagreed on the amount.
        bank("st#3", "-1150000", "INTERNET BILL 0227814455", has_conflict=True),
        # Nothing in the booking's words names the line.
        bank("st#4", "-368000", "WATER BILL 4471-0938"),
        # Another bank account's line.
        MatchRecord(
            "st#5",
            "BANK",
            D("-25000"),
            DAY,
            "IDR",
            description="ADMIN FEE",
            account_id="BCA ••0001",
        ),
        # Too far from the booking.
        bank("st#6", "-3126000", "ELECTRICITY BILL", DAY + timedelta(days=9)),
    ]
    entries = [
        entry("le#1", "1750000", "Cash sales deposit", DAY + timedelta(days=1)),
        entry("le#2", "1750000", "Cash sales deposit", DAY + timedelta(days=3)),
        entry("le#3", "-1150000", "Internet bill"),
        entry("le#4", "-368000", "Journal 2026-08-013"),
        entry("le#5", "-25000", "Admin fee"),
        entry("le#6", "-3126000", "Electricity bill"),
    ]

    assert run(lines, entries) == []


def test_lines_a_document_explains_and_rejected_matches_are_left_alone():
    lines = [bank("st#1", "2500000", "CASH DEPOSIT"), bank("st#2", "-15000000", "WAREHOUSE RENT")]
    entries = [
        entry("le#1", "2500000", "Cash deposit"),
        entry("le#2", "-15000000", "Warehouse rent"),
    ]
    rejected = frozenset({match_key(("st#2",), ("le#2",))})

    assert run(lines, entries, taken=frozenset({"st#1"}), rejected=rejected) == []


def test_the_result_does_not_depend_on_the_order_of_the_records():
    lines = [
        bank(f"st#{i}", str(100000 * (i + 1)), f"CASH DEPOSIT {i}", DAY + timedelta(days=i * 6))
        for i in range(5)
    ]
    entries = [
        entry(f"le#{i}", str(100000 * (i + 1)), "Cash deposit", DAY + timedelta(days=i * 6))
        for i in range(5)
    ]

    assert run(lines, entries) == run(lines[::-1], entries[::-1])
    assert len(run(lines, entries)) == 5
