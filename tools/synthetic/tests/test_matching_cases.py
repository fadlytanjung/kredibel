"""The special matching cases exist and mean what truth.json says (AC-002-7, AC-002-13)."""

from decimal import Decimal

import pytest

from kredibel_synth.matching_cases import (
    _decide,
    policy,
    score_invoice,
    score_receipt,
    unambiguous_amounts,
)
from tests.conftest import SEEDS, books_for


def _bank_doc(seed: int):
    return [
        m for m in books_for(seed).matches if m.kind.startswith("BANK_") and m.kind != "BANK_LEDGER"
    ]


@pytest.mark.parametrize("seed", SEEDS)
def test_ac002_7_the_six_cases_exist(seed: int):
    books = books_for(seed)
    matches = _bank_doc(seed)
    [net] = [m for m in matches if "NET_OF_TAX" in m.reasons]
    assert (net.month, net.expect) == ("2026-03", "AUTO")
    [split] = [m for m in matches if "SPLIT" in m.reasons]
    assert (split.month, len(split.bank), len(split.documents), split.expect) == (
        "2026-04",
        2,
        1,
        "AUTO",
    )
    [multi] = [
        m for m in matches if len(m.bank) == 1 and len(m.documents) == 2 and m.expect == "AUTO"
    ]
    assert multi.month == "2026-05"
    [proposed] = [m for m in matches if m.expect == "PROPOSED"]
    assert proposed.month == "2026-02" and len(proposed.documents) == 2
    [missing] = [r for r in books.bank_rows if not r.in_ledger]
    assert missing.key not in {k for m in books.matches if m.kind == "BANK_LEDGER" for k in m.bank}
    paid = {d for m in matches for d in m.documents}
    unpaid = [inv.key for inv in books.invoices if inv.key not in paid]
    assert unpaid == ["inv-sales-2026-06-04"]
    not_due = next(inv for inv in books.sales if inv.key == "inv-sales-2026-06-04")
    assert (not_due.issue_date.isoformat(), not_due.due_date.isoformat()) == (
        "2026-06-25",
        "2026-07-25",
    )


@pytest.mark.parametrize("seed", SEEDS)
def test_ac002_13_auto_matches_are_unambiguous_and_proposed_ones_are_ties(seed: int):
    books = books_for(seed)
    rows = {r.key: r for r in books.bank_rows}
    margin = policy().margin
    for m in _bank_doc(seed):
        if len(m.bank) != 1 or len(m.documents) > 2 and m.expect == "AUTO":
            continue
        row = rows[m.bank[0]]
        if m.kind == "BANK_RECEIPT":
            rec = next(r for r in books.receipts if r.key == m.documents[0])
            best = score_receipt(row, rec)
            rivals = [s for r in books.receipts if r.key != rec.key if (s := score_receipt(row, r))]
        elif len(m.documents) == 1:
            pool = books.sales if m.kind == "BANK_SALES_INVOICE" else books.purchases
            inv = next(i for i in pool if i.key == m.documents[0])
            best = score_invoice(row, inv)
            rivals = [s for i in pool if i.key != inv.key if (s := score_invoice(row, i))]
        else:
            if m.expect == "PROPOSED":
                pool = books.sales
                scores = [score_invoice(row, i) for i in pool if i.key in m.documents]
                assert all(s is not None for s in scores)
                top = [s.score for s in scores if s]
                assert max(top) - min(top) < margin and max(top) >= policy().propose
            continue
        assert best is not None
        assert _decide(best, rivals) == m.expect, m
        if m.expect == "AUTO":
            assert best.score >= policy().auto
            assert max((r.score for r in rivals), default=Decimal(0)) < best.score - margin


@pytest.mark.parametrize("seed", SEEDS)
def test_ac002_13_each_bank_line_has_exactly_its_own_ledger_candidate(seed: int):
    assert unambiguous_amounts(books_for(seed)) == []


@pytest.mark.parametrize("seed", SEEDS)
def test_every_document_and_ledger_booking_is_an_intended_match(seed: int):
    books = books_for(seed)
    linked = {d for m in books.matches if m.kind == "DOCUMENT_LEDGER" for d in m.documents}
    assert linked == {d.key for d in [*books.invoices, *books.receipts]}
