"""Content duplicates (spec 006, AC-006-1…3): when two files hold the same statement or invoice."""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain.checks.policy import Duplicates
from app.domain.duplicates import (
    InvoiceKey,
    ReceiptKey,
    StatementKey,
    invoice_duplicate,
    receipt_duplicate,
    statement_duplicate,
)

POLICY = Duplicates()
EARLIER, LATER = datetime(2026, 4, 1, tzinfo=UTC), datetime(2026, 4, 2, tzinfo=UTC)
ROWS = frozenset({(date(2026, 3, 5), Decimal("-12.40"), Decimal("100.00"))})


def _st(doc: str, start: date, end: date, *, when=LATER, rows=ROWS, last4="4821") -> StatementKey:
    return StatementKey(doc, when, "Archipelago Commerce Bank", last4, start, end, rows)


def test_overlapping_periods_of_one_account_are_a_duplicate_adjacent_ones_are_not():
    old = _st("doc_a", date(2026, 3, 1), date(2026, 3, 31), when=EARLIER)
    same = statement_duplicate(_st("doc_b", date(2026, 3, 1), date(2026, 3, 31)), [old], POLICY)
    assert same is not None and (same.code, same.severity, same.of_doc_id) == (
        "D02_STATEMENT_PERIOD_DUPLICATE",
        "MEDIUM",
        "doc_a",
    )
    assert (
        statement_duplicate(_st("doc_b", date(2026, 4, 1), date(2026, 4, 30)), [old], POLICY)
        is None
    )
    assert (
        statement_duplicate(
            _st("doc_b", date(2026, 3, 1), date(2026, 3, 31), last4="9999"), [old], POLICY
        )
        is None
    )


def test_overlapping_rows_that_differ_make_it_high():
    inside = frozenset({(date(2026, 3, 20), Decimal("-12.40"), Decimal("100.00"))})
    edited = frozenset({(date(2026, 3, 20), Decimal("-99.40"), Decimal("13.00"))})
    old = _st("doc_a", date(2026, 3, 1), date(2026, 3, 31), when=EARLIER, rows=inside)
    new = _st("doc_b", date(2026, 3, 15), date(2026, 4, 14), rows=edited)
    match = statement_duplicate(new, [old], POLICY)
    assert match is not None and match.severity == "HIGH"
    assert match.facts["overlapDays"] == "17" and match.facts["rowsOnlyHere"] == "1"


def test_only_the_newer_document_is_held():
    newer = _st("doc_b", date(2026, 3, 1), date(2026, 3, 31))
    assert (
        statement_duplicate(
            _st("doc_a", date(2026, 3, 1), date(2026, 3, 31), when=EARLIER), [newer], POLICY
        )
        is None
    )


def _inv(
    doc: str,
    number: str | None,
    day: date,
    total: str,
    when=LATER,
    issuer="Sunrise Coffee Roasters",
):
    return InvoiceKey(doc, when, issuer, number, day, Decimal(total))


def test_the_same_invoice_again_is_held_a_reused_number_keeps_both():
    old = _inv("doc_a", "INV/SCR/2026/03/0009", date(2026, 3, 12), "19597050.00", when=EARLIER)
    again = invoice_duplicate(
        _inv("doc_b", "INV-SCR-2026-03-0009", date(2026, 3, 12), "19597050.00"), [old], POLICY
    )
    assert again is not None and (again.code, again.hold) == ("D03_INVOICE_DUPLICATE", True)
    reused = invoice_duplicate(
        _inv("doc_b", "INV/SCR/2026/03/0009", date(2026, 3, 20), "500.00"), [old], POLICY
    )
    assert reused is not None and (reused.code, reused.severity, reused.hold) == (
        "D04_INVOICE_NUMBER_REUSED",
        "HIGH",
        False,
    )
    no_number = invoice_duplicate(
        _inv("doc_b", None, date(2026, 3, 12), "19597050.00", issuer="SUNRISE COFFEE ROASTERS"),
        [old],
        POLICY,
    )
    assert no_number is not None and no_number.code == "D03_INVOICE_DUPLICATE"
    other_issuer = _inv(
        "doc_b", "INV/SCR/2026/03/0009", date(2026, 3, 12), "19597050.00", issuer="Daybreak Café"
    )
    assert invoice_duplicate(other_issuer, [old], POLICY) is None


def _rc(doc: str, total: str, when=LATER, p_hash: str | None = None) -> ReceiptKey:
    return ReceiptKey(doc, when, "KEDAI RUNCIT MAJU", date(2026, 9, 12), Decimal(total), p_hash)


def test_a_receipt_with_the_same_merchant_date_and_total_within_a_unit_is_held():
    old = _rc("doc_a", "5.50", when=EARLIER)
    assert receipt_duplicate(_rc("doc_b", "6.40"), [old], POLICY) is not None
    assert receipt_duplicate(_rc("doc_b", "6.60"), [old], POLICY) is None


def test_a_receipt_photo_close_to_another_is_held_by_its_image_hash():
    old = ReceiptKey("doc_a", EARLIER, None, None, None, "ff00ff00ff00ff00")
    near = ReceiptKey("doc_b", LATER, None, None, None, "ff00ff00ff00ffff")  # 8 bits apart
    assert receipt_duplicate(near, [old], POLICY) is not None
    nine = ReceiptKey("doc_b", LATER, None, None, None, "ff00ff00ff01ffff")  # 9 bits apart
    assert receipt_duplicate(nine, [old], POLICY) is None


@pytest.mark.parametrize(
    "changed",
    [
        {"merchant": "Swift Courier"},
        {"day": date(2026, 9, 13)},
        {"total": Decimal("6.51")},
    ],
)
def test_matching_layout_does_not_override_different_receipt_values(changed):
    old = _rc("doc_a", "5.50", when=EARLIER, p_hash="ff00ff00ff00ff00")
    new = replace(old, doc_id="doc_b", uploaded_at=LATER, **changed)
    assert receipt_duplicate(new, [old], POLICY) is None


def test_image_fallback_with_missing_fields_and_total_at_tolerance_still_holds():
    old = _rc("doc_a", "5.50", when=EARLIER, p_hash="ff00ff00ff00ff00")
    new = replace(old, doc_id="doc_b", uploaded_at=LATER, merchant=None, total=Decimal("6.50"))
    assert receipt_duplicate(new, [old], POLICY) is not None
