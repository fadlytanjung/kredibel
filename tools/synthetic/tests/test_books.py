"""The books add up (docs/18 §7, AC-002-4…6), for seeds 1–20."""

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

import pytest

from kredibel_synth import world
from kredibel_synth.model import ZERO
from tests.conftest import SEEDS, books_for


@pytest.mark.parametrize("seed", SEEDS)
def test_ac002_4_every_row_satisfies_the_running_balance_and_months_continue(seed: int):
    books = books_for(seed)
    previous_closing = None
    for month in world.MONTHS:
        st = books.statements[month]
        balance = st.opening
        for row in st.rows:
            balance = balance + (row.credit or ZERO) - (row.debit or ZERO)
            assert row.balance == balance, row.key
        assert st.opening + st.total_credits - st.total_debits == st.closing
        if previous_closing is not None:
            assert st.opening == previous_closing, month
        previous_closing = st.closing
        assert min(r.balance for r in st.rows) >= Decimal("20000000")


@pytest.mark.parametrize("seed", SEEDS)
def test_ac002_1_the_counts_of_a_half_year(seed: int):
    books = books_for(seed)
    assert len(books.statements) == 6
    assert len(books.sales) == 24
    assert len(books.purchases) == 16
    assert len(books.receipts) == 24
    assert Counter(r.key[8:15] for r in books.receipts) == {m: 4 for m in world.MONTHS}
    assert all(22 <= len(st.rows) <= 32 for st in books.statements.values())


@pytest.mark.parametrize("seed", SEEDS)
def test_ac002_5_invoices_and_receipts_add_up(seed: int):
    books = books_for(seed)
    for doc in [*books.invoices, *books.receipts]:
        lines = doc.lines if hasattr(doc, "lines") else doc.items
        assert all(line.amount == line.unit_price * line.quantity for line in lines)
        assert doc.subtotal == sum((line.amount for line in lines), ZERO)
        assert abs(doc.vat - doc.subtotal * world.VAT_RATE) <= Decimal("0.5")
        assert doc.total == doc.subtotal + doc.vat
    assert {
        inv.pay_to.account_number
        for inv in books.purchases
        if inv.issuer == world.GREEN_VALLEY.party
    } == {"9900007312"}
    assert {r.payment.split()[0] for r in books.receipts} <= {"CASH", "DEBIT", "QRIS"}


@pytest.mark.parametrize("seed", SEEDS)
def test_ac002_6_every_bank_line_has_one_ledger_cash_entry_except_the_missing_deposit(seed: int):
    books = books_for(seed)
    cash = [e for e in books.ledger if e.account == "1110"]
    by_bank = defaultdict(list)
    for entry in cash:
        by_bank[entry.bank_key].append(entry)
    missing = [row for row in books.bank_rows if not by_bank.get(row.key)]
    assert [(row.date, row.description) for row in missing] == [(date(2026, 6, 21), "CASH DEPOSIT")]
    assert all(not row.in_ledger for row in missing)
    for row in books.bank_rows:
        if not row.in_ledger:
            continue
        [entry] = by_bank[row.key]
        assert entry.amount == row.amount
        assert 0 <= (entry.date - row.date).days <= 2
        assert (entry.debit is not None) == (row.credit is not None)


@pytest.mark.parametrize("seed", SEEDS)
def test_ac002_6_documents_post_to_their_accounts_and_every_journal_balances(seed: int):
    books = books_for(seed)
    booked = {e.document_key: e for e in books.ledger if e.document_key}
    for inv in books.sales:
        assert (booked[inv.key].account, booked[inv.key].debit) == ("1200", inv.total)
    for inv in books.purchases:
        assert (booked[inv.key].account, booked[inv.key].credit) == ("2100", inv.total)
    for rec in books.receipts:
        assert booked[rec.key].account in {"6100", "6200", "6300", "6400", "6500"}
    journals: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for e in books.ledger:
        journals[e.journal] += (e.debit or ZERO) - (e.credit or ZERO)
    assert all(v == ZERO for v in journals.values())
    refs = [e for e in books.ledger if e.journal.startswith("BNK") and e.account == "1110"]
    with_ref = sum(1 for e in refs if e.reference) / len(refs)
    assert 0.3 < with_ref < 0.9  # a bookkeeper types a reference most of the time


def test_the_row_t1_edits_exists():
    for seed in SEEDS:
        march = books_for(seed).statements["2026-03"].rows
        anchors = [
            r
            for r in march
            if r.date == world.T1_ANCHOR_DATE and r.credit == world.T1_ANCHOR_AMOUNT
        ]
        assert len(anchors) == 1
