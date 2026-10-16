"""Indonesian and Malay bank descriptions (spec 023): cash withdrawals are money out (product
decision 16 Oct 2026), fees, tax and interest have their local words. Synthetic descriptions."""

from decimal import Decimal as D
from pathlib import Path

import pytest

from app.adapters.policy_files import load_category_policy
from app.domain.categorize import by_rules

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts"


@pytest.fixture(scope="module")
def policy():
    return load_category_policy(CONTRACTS / "policy" / "categories.v1.yaml", CONTRACTS / "policy")


@pytest.mark.parametrize(
    "description,amount,category",
    [
        ("TRK TUNAI PMH 871597 SRI MULYA", "-6500000", "CASH_WITHDRAWAL"),
        ("TARIKAN TUNAI ATM BCA", "-500000", "CASH_WITHDRAWAL"),
        ("PENGELUARAN TUNAI", "-200000", "CASH_WITHDRAWAL"),
        ("ATM WITHDRAWAL 1234", "-300000", "CASH_WITHDRAWAL"),
        ("BIAYA ADM", "-30000", "BANK_FEES"),
        ("BIAYA TRANSFER BI-FAST", "-2500", "BANK_FEES"),
        ("PAJAK JASA GIRO OCT2022", "-617", "TAX_PAYMENT"),
        ("PPH CV CONTOH JAYA", "-148200", "TAX_PAYMENT"),
        ("JASA GIRO OCT2022", "1147.81", "INTEREST_RECEIVED"),
    ],
)
def test_local_words_decide_the_category(policy, description, amount, category):
    decided, _ = by_rules(description, None, D(amount), policy)
    assert decided is not None and decided.category == category


def test_a_cash_deposit_is_tagged_and_left_to_the_model(policy):
    decided, tags = by_rules("SETORAN TUNAI CONTOH", None, D("44180182"), policy)
    assert decided is None and tags == ["CASH_DEPOSIT"]


def test_a_cash_withdrawal_counts_as_money_out(policy):
    assert policy.categories["CASH_WITHDRAWAL"].cashflow_class("IFRS") == "OPERATING"
