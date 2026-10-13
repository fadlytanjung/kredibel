"""A person corrects a value read from an invoice or receipt (spec 009, T009-03a, AC-009-5)."""

from datetime import UTC, date, datetime
from decimal import Decimal as D

import pytest

from app.domain.corrections import correct_record, keep_corrections
from app.domain.errors import ValidationProblem
from app.domain.models.invoice import Invoice, Receipt

AT = datetime(2026, 7, 2, 9, 0, tzinfo=UTC)


def receipt() -> Receipt:
    return Receipt(
        "rcp_17jun",
        "doc_photo",
        "CENDANA FUEL",
        date(2026, 6, 17),
        "2026-06",
        D("467976.00"),
        consensus={"total": {"status": "SINGLE_SOURCE", "raw": {"GEMINI": "467,976.00"}}},
    )


def invoice() -> Invoice:
    return Invoice(
        "inv_0042",
        "doc_bw42",
        "PURCHASE",
        "BW-0042",
        "Bluewater Trading Co.",
        "Sunrise Coffee Roasters",
        date(2026, 3, 30),
        "2026-03",
        D("990000.00"),
    )


def test_a_corrected_total_keeps_what_was_read():
    fixed = correct_record(receipt(), "total", "476976", by="uid_owner", at=AT)
    assert fixed.total == D("476976.00")
    assert fixed.consensus["total"]["raw"] == {"GEMINI": "467,976.00"}  # the reading stays
    assert (fixed.corrected_fields, fixed.corrected_by, fixed.corrected_at) == (
        ["total"],
        "uid_owner",
        AT,
    )


def test_a_corrected_date_moves_the_record_to_its_month():
    fixed = correct_record(invoice(), "issueDate", "2026-04-02", by="uid_owner", at=AT)
    assert (fixed.issue_date, fixed.month) == (date(2026, 4, 2), "2026-04")
    moved = correct_record(receipt(), "date", "2026-07-01", by="uid_owner", at=AT)
    assert moved.month == "2026-07"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("total", "abc"),
        ("total", "-5"),
        ("total", "0"),
        ("date", "17/06/2026"),
        ("merchantName", "X"),
    ],
)
def test_only_a_well_formed_total_or_date_is_accepted(field, value):
    with pytest.raises(ValidationProblem):
        correct_record(receipt(), field, value, by="uid_owner", at=AT)


def test_an_invoice_has_an_issue_date_not_a_date():
    with pytest.raises(ValidationProblem):
        correct_record(invoice(), "date", "2026-04-02", by="uid_owner", at=AT)


def test_reading_the_document_again_keeps_the_correction():
    fixed = correct_record(receipt(), "date", "2026-07-01", by="uid_owner", at=AT)
    reread = receipt()  # the reader returns what it read before
    (kept,) = keep_corrections([reread], [fixed])
    assert (kept.date, kept.month, kept.total) == (date(2026, 7, 1), "2026-07", D("467976.00"))
    assert kept.corrected_fields == ["date"] and kept.corrected_by == "uid_owner"
    assert keep_corrections([reread], [receipt()]) == [reread]  # nothing corrected, nothing kept
