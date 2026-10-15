"""Review item rules and sync (spec 009, T009-01, AC-009-1, AC-009-3; docs/08 §7). Synthetic."""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal as D

from app.domain.review_items import (
    HeldCopy,
    LineFacts,
    ProposalFacts,
    RecordFacts,
    ReviewItemResolution,
    calculate_item_priority,
    compute_item_id,
    month_items,
    sync_items,
)

NOW = datetime(2026, 7, 2, 9, 0, tzinfo=UTC)


def items(**facts):
    defaults = {"lines": [], "records": [], "proposals": [], "held": []}
    return month_items(month="2026-04", currency="IDR", risk_level="LOW", **(defaults | facts))


def invoice(payment: str | None, **extra) -> RecordFacts:
    base = RecordFacts(
        "inv_bw1", "doc_bw1", "PURCHASE", "BW-0042", date(2026, 4, 3), D("4250000"), payment
    )
    return replace(base, **extra)


def test_ids_are_deterministic_and_differ_by_kind():
    assert compute_item_id("PROPOSED_MATCH", "mat_1") == compute_item_id("PROPOSED_MATCH", "mat_1")
    assert compute_item_id("PROPOSED_MATCH", "mat_1") != compute_item_id(
        "UNMATCHED_DOCUMENT", "mat_1"
    )
    assert compute_item_id("PROPOSED_MATCH", "mat_1").startswith("itm_")


def test_duplicates_first_then_items_of_risky_months():
    assert calculate_item_priority("POSSIBLE_DUPLICATE", "LOW") == 100
    assert calculate_item_priority("POSSIBLE_DUPLICATE", "CRITICAL") == 100
    assert calculate_item_priority("UNMATCHED_DOCUMENT", "CRITICAL") > calculate_item_priority(
        "PROPOSED_MATCH", "LOW"
    )


def test_an_unpaid_invoice_is_an_item_a_waiting_or_not_due_one_is_not():
    """AC-009-3: no statement covering its window means waiting, not unpaid."""
    (item,) = items(records=[invoice("UNPAID")])
    assert item.kind == "UNMATCHED_DOCUMENT"
    assert item.title == "Invoice BW-0042 of IDR 4,250,000.00 is unpaid after its due date"
    assert item.subject.invoice_ids == ["inv_bw1"] and item.allowed_actions == [
        "MATCH",
        "NOT_YET_PAID",
        "IGNORE",
    ]
    for state in ("WAITING_FOR_STATEMENT", "NOT_DUE", "PAID_BANK", "PROPOSED", "PAID_CASH", None):
        assert items(records=[invoice(state)]) == [], state


def test_a_proposed_match_is_one_item_and_its_records_get_none_of_their_own():
    proposal = ProposalFacts(
        "mat_feb",
        ("tx_9feb",),
        ("inv_0010",),
        (),
        D("19205109"),
        date(2026, 2, 9),
        D("0.82"),
        ("AMOUNT_NET_OF_TAX", "PARTY_MATCH"),
    )
    unpaid = replace(invoice("UNPAID"), record_id="inv_0010")
    (item,) = items(proposals=[proposal], records=[unpaid])
    assert item.kind == "PROPOSED_MATCH" and item.subject.match_id == "mat_feb"
    assert item.title == "Confirm the payment of IDR 19,205,109.00 on 9 Feb 2026"
    assert item.suggestion.candidates[0].reasons == ["AMOUNT_NET_OF_TAX", "PARTY_MATCH"]


def test_a_held_copy_is_the_only_item_for_its_records():
    copy = HeldCopy(
        "doc_copy", "D03_INVOICE_DUPLICATE", "doc_orig", "This invoice was already uploaded"
    )
    held_record = replace(invoice("UNPAID"), doc_id="doc_copy", held=True)
    (item,) = items(held=[copy], records=[held_record])
    assert (item.kind, item.doc_id, item.priority) == ("POSSIBLE_DUPLICATE", "doc_copy", 100)
    assert item.subject.doc_ids == ["doc_copy", "doc_orig"]
    assert item.allowed_actions == ["CONFIRM_DUPLICATE", "NOT_DUPLICATE"]


def test_an_uncertain_value_comes_before_the_unpaid_item_and_a_bank_match_settles_it():
    photo = RecordFacts(
        "rcp_17jun",
        "doc_photo",
        "RECEIPT",
        None,
        date(2026, 6, 17),
        D("467976"),
        "NO_BANK_MATCH",
        checks=(("total", "SINGLE_SOURCE"), ("date", "SINGLE_SOURCE")),
    )
    (item,) = items(records=[photo])
    assert item.kind == "LOW_CONFIDENCE_VALUE"
    assert item.title == "Check the date and total read from the receipt of 17 Jun 2026"
    assert item.subject.receipt_ids == ["rcp_17jun"] and item.subject.field == "total"
    # The bank paid exactly this total: the single reading is corroborated.
    assert items(records=[replace(photo, payment="PAID_BANK")]) == []
    # Two readings that disagree always need a person.
    conflict = replace(photo, payment="PAID_BANK", checks=(("total", "CONFLICT"),))
    assert [i.kind for i in items(records=[conflict])] == ["LOW_CONFIDENCE_VALUE"]


def test_missing_support_alone_is_informational_a_line_a_check_names_is_an_item():
    """ADR-025: only a specific requirement makes an unsupported line an item."""
    deposit = LineFacts("tx_21jun", "doc_jun", date(2026, 6, 21), D("12500000"), "NO_SUPPORT")
    assert items(lines=[deposit]) == []
    (item,) = items(lines=[replace(deposit, cited_by=("X09_LEDGER_BANK_DIFFERENCE",))])
    assert item.kind == "UNMATCHED_BANK_LINE"
    assert item.title == "IDR 12,500,000.00 received on 21 Jun 2026 has no supporting document"
    assert items(lines=[replace(deposit, support="NOT_REQUIRED", cited_by=("X09",))]) == []
    assert items(lines=[replace(deposit, held=True, cited_by=("X09",))]) == []


def test_sync_closes_items_whose_cause_is_gone_and_reopens_them_when_it_returns():
    (item,) = items(records=[invoice("UNPAID")])
    stored = sync_items([], [item], now=NOW)
    assert [i.status for i in stored] == ["OPEN"]

    paid = sync_items(stored, [], now=NOW)
    (closed,) = paid
    assert closed.status == "RESOLVED" and closed.resolution is not None
    assert (closed.resolution.resolved_by, closed.resolution.action) == ("system", None)
    assert sync_items(paid, [], now=NOW) == []  # nothing to rewrite

    (again,) = sync_items(paid, [item], now=NOW)
    assert again.status == "OPEN" and again.resolution is None


def test_sync_never_reopens_what_a_person_resolved():
    (item,) = items(records=[invoice("UNPAID")])
    decided = replace(
        item,
        status="RESOLVED",
        resolution=ReviewItemResolution("NOT_YET_PAID", "uid_owner", NOW, "Paid next week"),
    )
    assert sync_items([decided], [item], now=NOW) == []
    dismissed = replace(item, status="DISMISSED")
    assert sync_items([dismissed], [item], now=NOW) == []
