"""The review queue through the API (spec 009, T009-03, T009-04; AC-009-2, AC-009-5, AC-009-6).

Synthetic records; the items come from the domain rules, the decisions go to the services that
own them, and every resolution re-runs its month.
"""

import datetime as dt
from decimal import Decimal

from app.adapters.cloud_tasks import InlineTaskQueue
from app.domain.models.bank_line import BankLine
from app.domain.models.document import (
    DocStatus,
    DocType,
    Document,
    DuplicateDecision,
    DuplicateInfo,
    DuplicateKind,
)
from app.domain.models.invoice import Invoice, Receipt
from app.domain.models.match import StoredMatch
from app.domain.review_items import HeldCopy, ProposalFacts, RecordFacts, month_items
from tests.fakes.match_repository import FakeMatchRepository
from tests.fakes.record_repository import FakeRecords
from tests.fakes.review_item_repository import FakeReviewItemRepository
from tests.integration.test_invoice_workflow import AUTH, _client, _deps

ORG, MONTH = "org_1", "2026-03"
NOW = dt.datetime(2026, 4, 2, tzinfo=dt.UTC)


def _line(tx_id: str, amount: str, day: int) -> BankLine:
    return BankLine(
        tx_id=tx_id,
        doc_id="doc_stmt",
        page=1,
        row_index=day,
        date=dt.date(2026, 3, day),
        month=MONTH,
        amount=Decimal(amount),
        balance=None,
        description="TRANSFER TO SUPPLIER CO",
        counterparty_name="SUPPLIER CO",
    )


def _invoice(invoice_id: str, doc_id: str, total: str, payment: str) -> Invoice:
    return Invoice(
        invoice_id=invoice_id,
        doc_id=doc_id,
        kind="PURCHASE",
        number=f"INV-{invoice_id[-4:]}",
        issuer_name="SUPPLIER CO",
        buyer_name="SUNRISE COFFEE ROASTERS",
        issue_date=dt.date(2026, 3, 2),
        month=MONTH,
        total=Decimal(total),
        due_date=dt.date(2026, 3, 16),
        currency="IDR",
        evidence={"payment": payment},
    )


async def _seed(deps):
    """A net-of-tax proposal, an unpaid bill, a line for it, and a held copy of an invoice."""
    lines = [_line("tx_0321", "-1470000.00", 21), _line("tx_0325", "-990000.00", 25)]
    await deps.bank_lines.replace_document_lines(ORG, "doc_stmt", lines)
    proposed = _invoice("inv_0315", "doc_inv1", "1500000.00", "PROPOSED")
    unpaid = _invoice("inv_0316", "doc_inv2", "990000.00", "UNPAID")
    await deps.invoices.replace_for_document(ORG, "doc_inv1", [proposed])
    await deps.invoices.replace_for_document(ORG, "doc_inv2", [unpaid])
    deps.matches.matches[(ORG, "mat_net")] = StoredMatch(
        match_id="mat_net",
        month=MONTH,
        kind="BANK_PURCHASE_INVOICE",
        status="PROPOSED",
        method=None,
        bank_line_ids=["tx_0321"],
        invoice_ids=["inv_0315"],
        amount=Decimal("1470000.00"),
        amount_difference=Decimal("-30000.00"),
        score=Decimal("0.82"),
        reasons=["NET_OF_TAX", "PARTY_MATCH"],
    )
    copy = Document(
        doc_id="doc_copy",
        file_name="invoice-copy.pdf",
        content_type="application/pdf",
        size_bytes=1000,
        page_count=1,
        sha256="b" * 64,
        gcs_path="gs://synthetic/doc_copy.pdf",
        uploaded_by="u-1",
        uploaded_at=NOW,
        doc_type=DocType.PURCHASE_INVOICE,
        status=DocStatus.DONE,
        months=[MONTH],
        duplicate=DuplicateInfo(
            DuplicateKind.CONTENT, "D03_INVOICE_DUPLICATE", "doc_inv2", DuplicateDecision.PENDING
        ),
        held_as_duplicate=True,
    )
    await deps.doc_repo.save_document(ORG, copy)
    held_record = _invoice("inv_copy", "doc_copy", "990000.00", "UNPAID")
    await deps.invoices.replace_for_document(ORG, "doc_copy", [held_record])
    await deps.invoices.set_held(ORG, "doc_copy", True)

    facts = month_items(
        month=MONTH,
        currency="IDR",
        risk_level="LOW",
        lines=[],
        records=[
            RecordFacts(
                "inv_0316",
                "doc_inv2",
                "PURCHASE",
                "INV-0316",
                dt.date(2026, 3, 2),
                Decimal("990000.00"),
                "UNPAID",
            )
        ],
        proposals=[
            ProposalFacts(
                "mat_net",
                ("tx_0321",),
                ("inv_0315",),
                (),
                Decimal("1470000.00"),
                dt.date(2026, 3, 21),
                Decimal("0.82"),
                ("NET_OF_TAX", "PARTY_MATCH"),
            )
        ],
        held=[HeldCopy("doc_copy", "D03_INVOICE_DUPLICATE", "doc_inv2", "Invoice copy")],
    )
    await deps.review_items.replace_month_review_items(ORG, MONTH, facts, now=NOW)
    return {i.kind: i.item_id for i in facts}


def _fakes(deps) -> tuple[FakeMatchRepository, FakeReviewItemRepository, FakeRecords[Invoice]]:
    assert isinstance(deps.matches, FakeMatchRepository)
    assert isinstance(deps.review_items, FakeReviewItemRepository)
    assert isinstance(deps.invoices, FakeRecords)
    return deps.matches, deps.review_items, deps.invoices


def _month_tasks(deps) -> list[str]:
    queue = deps.task_queue
    assert isinstance(queue, InlineTaskQueue)
    return [t["month"] for t in queue.enqueued_month_tasks]


async def test_the_queue_lists_duplicates_first_with_counts_per_kind():
    deps, _ = _deps()
    await _seed(deps)
    async with _client(deps) as client:
        page = (await client.get("/api/review-items?status=OPEN", headers=AUTH)).json()
        only = await client.get("/api/review-items?kind=PROPOSED_MATCH&status=OPEN", headers=AUTH)

    assert [i["kind"] for i in page["items"]] == [
        "POSSIBLE_DUPLICATE",
        "PROPOSED_MATCH",
        "UNMATCHED_DOCUMENT",
    ]
    assert page["countsByKind"] == {
        "POSSIBLE_DUPLICATE": 1,
        "PROPOSED_MATCH": 1,
        "UNMATCHED_DOCUMENT": 1,
    }
    assert [i["kind"] for i in only.json()["items"]] == ["PROPOSED_MATCH"]
    assert only.json()["countsByKind"]["UNMATCHED_DOCUMENT"] == 1  # chips keep their counts


async def test_confirming_a_proposal_makes_it_the_persons_match_and_reruns_the_month():
    deps, _ = _deps()
    ids = await _seed(deps)
    async with _client(deps) as client:
        res = await client.post(
            f"/api/review-items/{ids['PROPOSED_MATCH']}/resolve",
            json={"action": "CONFIRM_MATCH"},
            headers=AUTH,
        )
        again = await client.post(
            f"/api/review-items/{ids['PROPOSED_MATCH']}/resolve",
            json={"action": "CONFIRM_MATCH"},
            headers=AUTH,
        )

    assert res.status_code == 200, res.text
    assert res.json()["status"] == "RESOLVED"
    assert res.json()["resolution"]["action"] == "CONFIRM_MATCH"
    matches, items, _ = _fakes(deps)
    match = matches.matches[(ORG, "mat_net")]
    assert (match.status, match.method, match.created_by) == ("CONFIRMED", "MANUAL", "u-1")
    assert "NET_OF_TAX" in match.reasons  # a confirmed net-of-tax match pays in full (ADR-025)
    assert [e.type for e in matches.events] == ["MATCH_CONFIRMED"]
    assert [e.type for e in items.events] == ["REVIEW_ITEM_RESOLVED"]
    assert MONTH in _month_tasks(deps)
    assert again.status_code == 409 and again.json()["code"] == "ITEM_ALREADY_RESOLVED"


async def test_only_the_kinds_actions_are_allowed_and_ignoring_needs_a_reason():
    deps, _ = _deps()
    ids = await _seed(deps)
    async with _client(deps) as client:
        wrong = await client.post(
            f"/api/review-items/{ids['UNMATCHED_DOCUMENT']}/resolve",
            json={"action": "CONFIRM_DUPLICATE"},
            headers=AUTH,
        )
        bare = await client.post(
            f"/api/review-items/{ids['UNMATCHED_DOCUMENT']}/resolve",
            json={"action": "IGNORE", "reason": "  "},
            headers=AUTH,
        )
        said = await client.post(
            f"/api/review-items/{ids['UNMATCHED_DOCUMENT']}/resolve",
            json={"action": "IGNORE", "reason": "Paid from the owner's card; refund agreed"},
            headers=AUTH,
        )

    assert wrong.status_code == 422 and wrong.json()["code"] == "ACTION_NOT_ALLOWED"
    assert wrong.json()["allowedActions"] == ["MATCH", "NOT_YET_PAID", "IGNORE"]
    assert bare.status_code == 422 and bare.json()["code"] == "REASON_REQUIRED"
    assert said.status_code == 200
    assert said.json()["resolution"]["note"] == "Paid from the owner's card; refund agreed"
    assert MONTH in _month_tasks(deps)  # an item-only decision still re-runs the month


async def test_a_manual_match_must_balance():
    deps, _ = _deps()
    ids = await _seed(deps)
    async with _client(deps) as client:
        off = await client.post(
            f"/api/review-items/{ids['UNMATCHED_DOCUMENT']}/resolve",
            json={"action": "MATCH", "bankLineIds": ["tx_0321"]},
            headers=AUTH,
        )
        even = await client.post(
            f"/api/review-items/{ids['UNMATCHED_DOCUMENT']}/resolve",
            json={"action": "MATCH", "bankLineIds": ["tx_0325"]},
            headers=AUTH,
        )

    assert off.status_code == 422 and off.json()["code"] == "MATCH_AMOUNT_MISMATCH"
    assert off.json()["difference"] == "480000.00"
    assert even.status_code == 200, even.text
    (manual,) = [m for m in _fakes(deps)[0].matches.values() if m.method == "MANUAL"]
    assert (manual.bank_line_ids, manual.invoice_ids) == (["tx_0325"], ["inv_0316"])


async def test_not_a_duplicate_releases_the_copy_and_its_records():
    deps, _ = _deps()
    ids = await _seed(deps)
    async with _client(deps) as client:
        res = await client.post(
            f"/api/review-items/{ids['POSSIBLE_DUPLICATE']}/resolve",
            json={"action": "NOT_DUPLICATE"},
            headers=AUTH,
        )

    assert res.status_code == 200, res.text
    doc = await deps.doc_repo.get_document(ORG, "doc_copy")
    assert doc is not None and doc.duplicate is not None
    assert (doc.held_as_duplicate, doc.duplicate.decision) == (False, DuplicateDecision.REJECTED)
    assert doc.duplicate.decided_by == "u-1"
    assert (ORG, "doc_copy") not in _fakes(deps)[2].held
    assert MONTH in _month_tasks(deps)


async def test_correcting_a_value_keeps_the_reading_and_reruns_the_months():
    deps, _ = _deps()
    await _seed(deps)
    receipt = Receipt(
        "rcp_17mar",
        "doc_photo",
        "CENDANA FUEL",
        dt.date(2026, 3, 17),
        MONTH,
        Decimal("467976.00"),
        consensus={"total": {"status": "SINGLE_SOURCE", "raw": {"GEMINI": "467,976.00"}}},
    )
    await deps.receipts.replace_for_document(ORG, "doc_photo", [receipt])
    (item,) = month_items(
        month=MONTH,
        currency="IDR",
        risk_level="LOW",
        lines=[],
        records=[
            RecordFacts(
                "rcp_17mar",
                "doc_photo",
                "RECEIPT",
                None,
                dt.date(2026, 3, 17),
                Decimal("467976.00"),
                "NO_BANK_MATCH",
                checks=(("total", "SINGLE_SOURCE"),),
            )
        ],
        proposals=[],
        held=[],
    )
    await deps.review_items.replace_month_review_items(ORG, MONTH, [item], now=NOW)
    async with _client(deps) as client:
        bad = await client.post(
            f"/api/review-items/{item.item_id}/resolve",
            json={"action": "CORRECT_VALUE", "field": "total", "value": "four hundred"},
            headers=AUTH,
        )
        res = await client.post(
            f"/api/review-items/{item.item_id}/resolve",
            json={"action": "CORRECT_VALUE", "field": "total", "value": "476976"},
            headers=AUTH,
        )
        listed = (await client.get("/api/receipts", headers=AUTH)).json()["items"]

    assert bad.status_code == 422
    assert res.status_code == 200, res.text
    (stored,) = [r for r in listed if r["receiptId"] == "rcp_17mar"]
    assert stored["total"] == {"amount": "476976.00", "currency": "IDR"}
    assert stored["correctedFields"] == ["total"]
    assert stored["readings"]["total"]["raw"] == {"GEMINI": "467,976.00"}
    assert isinstance(deps.receipts, FakeRecords)
    (event,) = deps.receipts.events
    assert (event.type, event.details) == ("VALUE_CORRECTED", {"field": "total"})
    assert MONTH in _month_tasks(deps)
