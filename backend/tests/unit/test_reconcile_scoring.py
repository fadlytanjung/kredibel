"""Policy and candidate eligibility (AC-007-5, AC-007-17, AC-007-19); synthetic inputs only."""

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal as D
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.adapters.policy_files import load_reconciliation_policy
from app.domain.reconcile_scoring import MatchRecord, score_pair
from app.domain.reconciliation_policy import ReconciliationPolicy

POLICY_DIR = Path(__file__).resolve().parents[3] / "contracts" / "policy"
DAY = date(2026, 3, 10)


@pytest.fixture
def policy():
    return load_reconciliation_policy(POLICY_DIR)


@pytest.fixture
def bank():
    return MatchRecord(
        "bank-1",
        "BANK",
        D("1000"),
        DAY,
        "MYR",
        party="Daybreak Café",
        description="TRANSFER DAYBREAK CAFE INV-12",
        account_id="account-demo",
    )


@pytest.fixture
def invoice():
    return MatchRecord(
        "invoice-1",
        "SALES_INVOICE",
        D("1000"),
        DAY,
        "MYR",
        party="DAYBREAK CAFE",
        reference="INV-12",
        due_date=DAY + timedelta(days=14),
    )


def test_ac007_5_all_components_and_evidence_are_inspectable(policy, bank, invoice):
    result = score_pair(bank, invoice, policy, workspace_currency="MYR")
    assert result is not None
    assert (result.amount, result.party, result.reference, result.date) == (D(1),) * 4
    assert result.score == D(1)
    assert result.reasons == ("AMOUNT_EXACT", "PARTY_MATCH", "REFERENCE_IN_TEXT", "DATE_NEAR")
    assert result.amount_difference == D(0)
    assert result.left_id == bank.record_id and result.right_id == invoice.record_id
    assert not result.requires_review


def test_ac007_17_amount_and_date_without_identity_cannot_auto_confirm(policy, bank, invoice):
    bank = replace(bank, party=None, description="")
    result = score_pair(bank, invoice, policy, workspace_currency="MYR")
    assert result is not None and result.score == D("0.60")
    assert result.score < policy.thresholds.auto_confirm_score


@pytest.mark.parametrize(
    "delta,expected", [(-6, None), (-5, "1"), (14, "1"), (29, "0.5"), (44, "0"), (45, None)]
)
def test_ac007_5_invoice_window_boundaries(policy, bank, invoice, delta, expected):
    result = score_pair(
        replace(bank, date=DAY + timedelta(days=delta)), invoice, policy, workspace_currency="MYR"
    )
    assert (None if result is None else result.date) == (None if expected is None else D(expected))


def test_ac007_5_missing_due_date_uses_policy_terms(policy, bank, invoice):
    invoice = replace(invoice, due_date=None)
    bank = replace(bank, date=DAY + timedelta(days=policy.windows.default_terms_days))
    result = score_pair(bank, invoice, policy, workspace_currency="MYR")
    assert result is not None and result.date == 1


@pytest.mark.parametrize(
    "description,expected",
    [
        ("PAID inv/12", 1),
        ("PAID INV-123", 0),
        ("PAID XINV-12", 0),
        ("INV-12A", 0),
        ("PAID INV 12", 1),
    ],
)
def test_ac007_17_reference_is_whole_not_substring(policy, bank, invoice, description, expected):
    result = score_pair(
        replace(bank, description=description), invoice, policy, workspace_currency="MYR"
    )
    assert result is not None and result.reference == expected


@pytest.mark.parametrize(
    "currency,total,paid,eligible",
    [
        ("MYR", "1", "1.01", True),
        ("MYR", "1", "1.011", False),
        ("MYR", "1000", "1005", True),
        ("MYR", "1000", "1005.01", False),
        ("IDR", "10000", "11000", True),
        ("IDR", "10000", "11001", False),
        ("JPY", "10", "11", True),
        ("JPY", "10", "12", False),
    ],
)
def test_ac007_17_tolerance_uses_workspace_currency(
    policy, bank, invoice, currency, total, paid, eligible
):
    result = score_pair(
        replace(bank, currency=currency, amount=D(paid)),
        replace(invoice, currency=currency, amount=D(total)),
        policy,
        workspace_currency=currency,
    )
    assert (result is not None) is eligible


def test_ac007_19_a_document_printing_no_currency_is_in_the_workspace_currency(
    policy, bank, invoice
):
    unprinted = replace(invoice, currency=None)
    result = score_pair(bank, unprinted, policy, workspace_currency="MYR")
    assert result is not None and result.score == D(1)
    assert unprinted.currency is None  # what the document prints is kept as it is


@pytest.mark.parametrize("currency", ["IDR", "EUR"])
def test_ac007_19_currency_override_needs_explicit_agreement(policy, bank, invoice, currency):
    foreign = replace(invoice, currency=currency)
    assert score_pair(bank, foreign, policy, workspace_currency="MYR") is None
    accepted = replace(foreign, currency_override_confirmed=True)
    result = score_pair(bank, accepted, policy, workspace_currency="MYR")
    assert result is not None and result.amount_difference == 0 and result.amount == 1
    assert accepted.currency == currency and accepted.amount == D("1000")
    # Acceptance relabels interpretation, never changes the numeric amount or uses the IDR floor.
    assert (
        score_pair(replace(bank, amount=D("1500")), accepted, policy, workspace_currency="MYR")
        is None
    )


def test_ac007_19_foreign_statement_requires_its_own_agreement(policy, bank, invoice):
    foreign = replace(bank, currency="IDR")
    assert score_pair(foreign, invoice, policy, workspace_currency="MYR") is None
    assert (
        score_pair(
            replace(foreign, currency_override_confirmed=True),
            invoice,
            policy,
            workspace_currency="MYR",
        )
        is not None
    )
    assert score_pair(bank, invoice, policy, workspace_currency="EUR") is None


@pytest.mark.parametrize(
    "change",
    [
        {"amount": D(0)},
        {"amount": None},
        {"amount": D("NaN")},
        {"amount": D("Infinity")},
        {"date": None},
        {"held": True},
        {"due_date": DAY - timedelta(days=1)},
        {"amount": D("-1000")},
    ],
)
def test_ac007_17_incomplete_or_invalid_documents_cannot_match(policy, bank, invoice, change):
    assert score_pair(bank, replace(invoice, **change), policy, workspace_currency="MYR") is None


def test_ac007_17_wrong_direction_and_held_bank_are_ineligible(policy, bank, invoice):
    assert (
        score_pair(replace(bank, amount=-bank.amount), invoice, policy, workspace_currency="MYR")
        is None
    )
    assert score_pair(replace(bank, held=True), invoice, policy, workspace_currency="MYR") is None
    assert (
        score_pair(
            replace(bank, amount=-bank.amount),
            replace(invoice, kind="PURCHASE_INVOICE"),
            policy,
            workspace_currency="MYR",
        )
        is not None
    )


@pytest.mark.parametrize("paid,score", [("980", "0.8"), ("979.99", None), ("995", "1")])
def test_ac007_17_tax_like_shortfall_needs_review(policy, bank, invoice, paid, score):
    result = score_pair(replace(bank, amount=D(paid)), invoice, policy, workspace_currency="MYR")
    if score is None:
        assert result is None
    else:
        assert result is not None and result.amount == D(score)
        assert result.requires_review is (score == "0.8")
        assert ("NET_OF_TAX" in result.reasons) is (score == "0.8")


def test_ac007_5_conflict_retains_candidate_but_prevents_automation(policy, bank, invoice):
    for left, right in [
        (replace(bank, has_conflict=True), invoice),
        (bank, replace(invoice, has_conflict=True)),
    ]:
        result = score_pair(left, right, policy, workspace_currency="MYR")
        assert result is not None and result.score == 1 and result.requires_review


@pytest.mark.parametrize("beyond", [-1, 0, 1])
def test_ac007_5_receipt_and_ledger_windows(policy, bank, invoice, beyond):
    """Receipts up to receiptDays apart (card settlements, spec 023); ledger cash ledgerDays."""
    receipt = replace(invoice, kind="RECEIPT", payment_method="CARD", due_date=None)
    cash = replace(bank, record_id="ledger-1", kind="LEDGER_CASH", amount=-bank.amount)
    windows = policy.windows
    for target, window in ((receipt, windows.receipt_days), (cash, windows.ledger_days)):
        for days in (-(window + beyond), window + beyond):
            debit = replace(bank, amount=-bank.amount, date=DAY + timedelta(days=days))
            result = score_pair(debit, target, policy, workspace_currency="MYR")
            assert (result is not None) is (beyond <= 0)
            if result is not None:
                assert result.date == 1 - D(abs(days)) / window


@pytest.mark.parametrize(
    "method,eligible", [("CASH", False), ("UNKNOWN", False), ("CARD", True), ("TRANSFER", True)]
)
def test_ac007_17_receipt_payment_method(policy, bank, invoice, method, eligible):
    result = score_pair(
        replace(bank, amount=-bank.amount),
        replace(invoice, kind="RECEIPT", payment_method=method),
        policy,
        workspace_currency="MYR",
    )
    assert (result is not None) is eligible


def test_ac007_17_receipts_and_ledger_do_not_assume_withholding(policy, bank, invoice):
    debit = replace(bank, amount=D("-980"))
    for target in [
        replace(invoice, kind="RECEIPT", payment_method="TRANSFER"),
        replace(bank, record_id="ledger-1", kind="LEDGER_CASH", amount=D("-1000")),
    ]:
        assert score_pair(debit, target, policy, workspace_currency="MYR") is None


@pytest.mark.parametrize("account", [None, "other-account"])
def test_ac007_17_ledger_cash_requires_same_confirmed_account(policy, bank, account):
    ledger = replace(bank, record_id="ledger-1", kind="LEDGER_CASH", account_id=account)
    assert score_pair(bank, ledger, policy, workspace_currency="MYR") is None


@pytest.mark.parametrize(
    "kind,role",
    [("SALES_INVOICE", "RECEIVABLE"), ("PURCHASE_INVOICE", "PAYABLE"), ("RECEIPT", "EXPENSE")],
)
def test_ac007_5_document_ledger_uses_booking_role_and_ledger_window(policy, invoice, kind, role):
    document = replace(invoice, kind=kind, payment_method="CASH")
    ledger = replace(
        invoice,
        record_id="ledger-1",
        kind="LEDGER_DOCUMENT",
        booking_role=role,
        description="BOOKING INV-12",
        reference=None,
    )
    assert score_pair(document, ledger, policy, workspace_currency="MYR") is not None
    assert (
        score_pair(
            document,
            replace(ledger, date=DAY + timedelta(days=policy.windows.ledger_days + 1)),
            policy,
            workspace_currency="MYR",
        )
        is None
    )
    assert (
        score_pair(document, replace(ledger, booking_role=None), policy, workspace_currency="MYR")
        is None
    )


def test_ac007_17_thresholds_come_from_validated_policy(bank, invoice):
    raw = yaml.safe_load((POLICY_DIR / "reconciliation.v1.yaml").read_text())
    raw["weights"] = {"amount": "0.2", "party": "0.3", "reference": "0.2", "date": "0.3"}
    policy = ReconciliationPolicy.model_validate(raw)
    result = score_pair(
        replace(bank, description="", party=None), invoice, policy, workspace_currency="MYR"
    )
    assert result is not None and result.score == D("0.5")
    raw["weights"]["amount"] = "0.9"
    with pytest.raises(ValidationError):
        ReconciliationPolicy.model_validate(raw)


@pytest.mark.parametrize(
    "section,key,value",
    [
        ("windows", "receiptDays", -1),
        ("thresholds", "autoConfirmScore", "1.1"),
        ("amountTolerance", "share", "NaN"),
        ("amountTolerance", "minimumByCurrency", {"MYR": "-1"}),
    ],
)
def test_ac007_17_invalid_policy_fails_closed(section, key, value):
    raw = yaml.safe_load((POLICY_DIR / "reconciliation.v1.yaml").read_text())
    raw[section][key] = value
    with pytest.raises(ValidationError):
        ReconciliationPolicy.model_validate(raw)
