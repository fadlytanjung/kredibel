"""Invoices and receipts on Firestore (docs/09 §3.7): round trip; a re-read replaces them."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from google.cloud.firestore import AsyncClient

from app.adapters.firestore.record_repo import firestore_invoices, firestore_receipts
from app.domain.models.invoice import Invoice, InvoiceLine, Receipt, ReceiptItem


def _invoice(n: int, doc: str = "doc_a", month: str = "2025-12") -> Invoice:
    return Invoice(
        invoice_id=f"inv_{n}",
        doc_id=doc,
        kind="SALES",
        number=f"INV-{n}",
        issuer_name="ACME SDN BHD",
        buyer_name="Kopi Kita",
        issue_date=date(2025, 12, 20 + n),
        month=month,
        total=Decimal("1908.00"),
        currency="MYR",
        tax=Decimal("108.00"),
        subtotal=Decimal("1800.00"),
        pay_to_masked="••••5678",
        issuer_tax_id="••••0042",
        supply_kind="SERVICES",
        pages=[n],
        lines=[InvoiceLine("Website design", Decimal("1"), Decimal("1200.00"), Decimal("1200.00"))],
        consensus={"total": {"status": "AGREED", "page": n, "bbox": None, "raw": {}}},
    )


@pytest.fixture
def db(firestore_emulator: str) -> AsyncClient:
    return AsyncClient(project=f"test-{uuid.uuid4().hex[:12]}")


async def test_invoices_round_trip_and_a_re_read_replaces_them(db):
    repo = firestore_invoices(db)
    await repo.replace_for_document("org_1", "doc_a", [_invoice(1), _invoice(2)])
    await repo.replace_for_document("org_1", "doc_b", [_invoice(9, "doc_b", "2026-01")])
    got = await repo.list_records("org_1", doc_id="doc_a")
    assert [i.invoice_id for i in got] == ["inv_1", "inv_2"]
    assert got[0] == _invoice(1)

    await repo.replace_for_document("org_1", "doc_a", [_invoice(2)])
    assert [i.invoice_id for i in await repo.list_records("org_1", doc_id="doc_a")] == ["inv_2"]
    assert [i.invoice_id for i in await repo.list_records("org_1", month="2026-01")] == ["inv_9"]


async def test_receipts_round_trip(db):
    repo = firestore_receipts(db)
    receipt = Receipt(
        receipt_id="rcp_1",
        doc_id="doc_r",
        merchant_name="KEDAI RUNCIT MAJU",
        date=date(2026, 9, 12),
        month="2026-09",
        total=Decimal("5.50"),
        currency="MYR",
        payment_method="TRANSFER",
        items=[ReceiptItem("Teh tarik", Decimal("3.50"))],
        pages=[1],
    )
    await repo.replace_for_document("org_1", "doc_r", [receipt])
    assert await repo.list_records("org_1", doc_id="doc_r") == [receipt]
