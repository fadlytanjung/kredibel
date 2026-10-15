"""Tests for manual match and unmatch API (spec 007, T007-09, AC-007-13)."""

import datetime as dt
from decimal import Decimal

from app.adapters.cloud_tasks import InlineTaskQueue
from app.domain.models.bank_line import BankLine
from app.domain.models.invoice import Invoice
from tests.integration.test_invoice_workflow import AUTH, _client, _deps


async def _seed_data(deps) -> tuple[str, str, str]:
    """Seed an invoice and bank line directly for testing."""
    org_id = "org_1"
    month = "2026-03"
    line = BankLine(
        tx_id="tx_test_01",
        doc_id="doc_stmt_01",
        page=1,
        row_index=1,
        date=dt.date(2026, 3, 21),
        month=month,
        amount=Decimal("-1500000.00"),
        balance=Decimal("10000000.00"),
        description="TRANSFER TO SUPPLIER",
        category="SUPPLIER",
        category_confidence=Decimal("0.9"),
        counterparty_name="SUPPLIER CO",
    )
    await deps.bank_lines.replace_document_lines(org_id, "doc_stmt_01", [line])

    invoice = Invoice(
        invoice_id="inv_test_01",
        doc_id="doc_inv_01",
        kind="PURCHASE",
        number="INV-2026-001",
        issuer_name="SUPPLIER CO",
        buyer_name="SUNRISE COFFEE",
        issue_date=dt.date(2026, 3, 15),
        month=month,
        total=Decimal("1500000.00"),
        due_date=dt.date(2026, 3, 30),
        currency="IDR",
        subtotal=Decimal("1500000.00"),
        tax=Decimal("0.00"),
    )
    await deps.invoices.replace_for_document(org_id, "doc_inv_01", [invoice])
    return month, line.tx_id, invoice.invoice_id


async def test_manual_match_creates_audited_match_and_reruns_month():
    deps, _ = _deps()
    month, tx_id, inv_id = await _seed_data(deps)
    async with _client(deps) as client:
        queue = deps.task_queue
        assert isinstance(queue, InlineTaskQueue)
        before = len(queue.enqueued_month_tasks)

        body = {
            "bankLineIds": [tx_id],
            "invoiceIds": [inv_id],
            "note": "Matched by accountant",
        }
        res = await client.post("/api/matches", json=body, headers=AUTH)
        assert res.status_code == 201, res.text
        created = res.json()
        assert created["method"] == "MANUAL"
        assert created["status"] == "CONFIRMED"
        assert created["kind"] == "BANK_PURCHASE_INVOICE"
        assert created["bankLineIds"] == [tx_id]
        assert created["invoiceIds"] == [inv_id]
        assert created["amount"] == {"amount": "1500000.00", "currency": "IDR"}
        assert created["amountDifference"] == {"amount": "0.00", "currency": "IDR"}

        # Audit event recorded
        events = deps.matches.events  # type: ignore[attr-defined]
        assert any(e.type == "MATCH_CREATED" for e in events)

        # Month task re-run enqueued
        assert any(t["month"] == month for t in queue.enqueued_month_tasks[before:])


async def test_manual_match_fails_if_already_matched():
    deps, _ = _deps()
    _, tx_id, inv_id = await _seed_data(deps)
    async with _client(deps) as client:
        body = {"bankLineIds": [tx_id], "invoiceIds": [inv_id]}
        res1 = await client.post("/api/matches", json=body, headers=AUTH)
        assert res1.status_code == 201

        # Trying to match again should fail with 409 Conflict
        res2 = await client.post("/api/matches", json=body, headers=AUTH)
        assert res2.status_code == 409
        err = res2.json()
        assert err["code"] == "ALREADY_MATCHED"


async def test_manual_match_fails_if_tolerance_exceeded():
    deps, _ = _deps()
    org_id = "org_1"
    # Create invoice with a total that significantly exceeds tolerance (e.g. 5,000,000 vs 1,500,000)
    inv_diff = Invoice(
        invoice_id="inv_diff_01",
        doc_id="doc_inv_diff",
        kind="PURCHASE",
        number="INV-DIFF-001",
        issuer_name="SUPPLIER CO",
        buyer_name="SUNRISE COFFEE",
        issue_date=dt.date(2026, 3, 15),
        month="2026-03",
        total=Decimal("5000000.00"),
        due_date=dt.date(2026, 3, 30),
        currency="IDR",
        subtotal=Decimal("5000000.00"),
        tax=Decimal("0.00"),
    )
    await deps.invoices.replace_for_document(org_id, "doc_inv_diff", [inv_diff])
    _, tx_id, _ = await _seed_data(deps)

    async with _client(deps) as client:
        body = {"bankLineIds": [tx_id], "invoiceIds": ["inv_diff_01"]}
        res = await client.post("/api/matches", json=body, headers=AUTH)
        assert res.status_code == 422
        err = res.json()
        assert err["code"] == "TOLERANCE_EXCEEDED"


async def test_unmatch_marks_match_rejected_and_reruns_month():
    deps, _ = _deps()
    month, tx_id, inv_id = await _seed_data(deps)
    async with _client(deps) as client:
        # First create a match
        body = {"bankLineIds": [tx_id], "invoiceIds": [inv_id]}
        res = await client.post("/api/matches", json=body, headers=AUTH)
        assert res.status_code == 201
        match_id = res.json()["matchId"]

        queue = deps.task_queue
        assert isinstance(queue, InlineTaskQueue)
        before = len(queue.enqueued_month_tasks)

        # Now unmatch it
        unmatch_res = await client.delete(f"/api/matches/{match_id}", headers=AUTH)
        assert unmatch_res.status_code == 204

        # Verify it became REJECTED in repo
        stored = await deps.matches.get("org_1", match_id)
        assert stored is not None
        assert stored.status == "REJECTED"
        assert stored.method == "MANUAL"

        # Audit event recorded
        events = deps.matches.events  # type: ignore[attr-defined]
        assert any(e.type == "MATCH_REJECTED" for e in events)

        # Month task re-run enqueued
        assert any(t["month"] == month for t in queue.enqueued_month_tasks[before:])
