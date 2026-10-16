"""Matching the real cases of spec 023: card settlements a few days late, a fee taken from a
payment, a known withholding rate, and several receipts paid in one charge. Synthetic data only."""

from datetime import date, timedelta
from decimal import Decimal as D
from pathlib import Path

import pytest

from app.adapters.policy_files import load_reconciliation_policy
from app.domain.reconcile import Decisions, assign_matches
from app.domain.reconcile_scoring import Kind, MatchRecord, score_pair

POLICY_DIR = Path(__file__).resolve().parents[3] / "contracts" / "policy"
DAY = date(2026, 3, 10)


@pytest.fixture
def policy():
    return load_reconciliation_policy(POLICY_DIR)


def _bank(
    amount: str, day: date = DAY, description: str = "TRANSFER DAYBREAK CAFE", party="Daybreak Cafe"
):
    return MatchRecord(
        "bank-1", "BANK", D(amount), day, "IDR", party=party, description=description
    )


def _invoice(total: str, kind: Kind = "SALES_INVOICE", record_id="inv-1", party="DAYBREAK CAFE"):
    return MatchRecord(
        record_id,
        kind,
        D(total),
        DAY,
        "IDR",
        party=party,
        reference=None,
        due_date=DAY + timedelta(days=14),
    )


def _receipt(record_id: str, total: str, day: date, party="Apple"):
    return MatchRecord(
        record_id, "RECEIPT", D(total), day, "IDR", party=party, payment_method="CARD"
    )


def test_ac023_2_a_card_receipt_settles_up_to_five_days_later(policy):
    receipt = _receipt("rcp-1", "150000", DAY, party="Corner Bakery")
    for days, matches in ((5, True), (6, False)):
        bank = _bank("-150000", DAY + timedelta(days=days), "QRIS CORNER BAKERY", "Corner Bakery")
        assert (score_pair(bank, receipt, policy, workspace_currency="IDR") is not None) is matches


def test_ac023_3_an_incoming_payment_short_by_a_bank_fee_is_a_proposal(policy):
    # 0.5% of a small invoice is less than a transfer fee; on a large one the tolerance covers it.
    scored = score_pair(_bank("493500"), _invoice("500000"), policy, workspace_currency="IDR")
    assert scored is not None and "FEE_DEDUCTED" in scored.reasons and scored.requires_review
    too_short = score_pair(_bank("480000"), _invoice("500000"), policy, workspace_currency="IDR")
    assert too_short is None or "FEE_DEDUCTED" not in too_short.reasons


def test_ac023_3_withholding_up_to_two_percent_or_at_a_known_higher_rate_is_a_proposal(policy):
    # PPh 23 2% and PPh 22 1.5% fall in the net-of-tax band; PPh 4(2) 10% is a known rate above it.
    cases = (("9800000", "NET_OF_TAX"), ("9850000", "NET_OF_TAX"), ("9000000", "WITHHOLDING_RATE"))
    for paid, reason in cases:
        scored = score_pair(
            _bank(f"-{paid}", party="Jaya Teknik", description="TRF JAYA TEKNIK"),
            _invoice("10000000", "PURCHASE_INVOICE", party="PT Jaya Teknik"),
            policy,
            workspace_currency="IDR",
        )
        assert scored is not None and reason in scored.reasons and scored.requires_review
    five_percent_short = score_pair(
        _bank("-9500000", party="Jaya Teknik", description="TRF JAYA TEKNIK"),
        _invoice("10000000", "PURCHASE_INVOICE", party="PT Jaya Teknik"),
        policy,
        workspace_currency="IDR",
    )
    assert five_percent_short is None, "5% short is no known rate"


def test_ac023_4_one_card_charge_settles_five_receipts_of_one_party_as_a_proposal(policy):
    amounts = ["49000", "79000", "149000", "15000", "29000"]
    receipts = [_receipt(f"rcp-{n}", a, DAY - timedelta(days=n % 3)) for n, a in enumerate(amounts)]
    others = [_receipt("rcp-x", "321000", DAY, party="Corner Bakery")]
    total = sum(D(a) for a in amounts)
    bank = _bank(f"-{total}", DAY + timedelta(days=2), "APPLE.COM/BILL ITUNES.COM", "Apple")

    [allocation] = assign_matches(
        [bank], [*receipts, *others], policy, workspace_currency="IDR", decisions=Decisions()
    )

    assert sorted(allocation.right_ids) == sorted(r.record_id for r in receipts)
    assert "GROUPED" in allocation.reasons
    assert allocation.status == "PROPOSED", "more than three parts is never automatic"


def test_ac023_5_the_party_score_uses_the_counterpartys_known_spellings(policy):
    invoice = _invoice("2500000", "PURCHASE_INVOICE", party="PT Jaya Teknik Mandiri")
    terse = MatchRecord(
        "bank-1", "BANK", D("-2500000"), DAY, "IDR", party="JYTK", description="TRF M-BKG 0206 JYTK"
    )
    known = MatchRecord(
        "bank-1",
        "BANK",
        D("-2500000"),
        DAY,
        "IDR",
        party="JYTK",
        description="TRF M-BKG 0206 JYTK",
        aliases=("PT Jaya Teknik Mandiri",),
    )
    without = score_pair(terse, invoice, policy, workspace_currency="IDR")
    with_aliases = score_pair(known, invoice, policy, workspace_currency="IDR")
    assert without is not None and with_aliases is not None
    assert with_aliases.party == 1 > without.party
    assert "PARTY_MATCH" in with_aliases.reasons
