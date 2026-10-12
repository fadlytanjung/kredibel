"""S1-generated PDFs and recorded readings; every repository is explicitly in memory.

Used by integration tests and scripts/demo_reconciliation.py. No real workspace or model access.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.domain.reading import (
    DocClassification,
    InvoiceLineReading,
    InvoicePageReading,
    ReceiptItemReading,
    ReceiptPageReading,
)
from app.ports.document_reader import ReaderCall
from tests.fakes.bank_line_repository import FakeBankLineRepository
from tests.fakes.decision_repository import FakeDecisionRepository
from tests.fakes.document_reader import FakeDocumentReader
from tests.fakes.finding_repository import FakeFindingRepository
from tests.fakes.match_repository import FakeMatchRepository
from tests.fakes.record_repository import fake_receipts
from tests.integration.test_invoice_workflow import _deps
from tests.integration.test_reading_workflow import _recorded_page

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/reconciliation"
DOCUMENTS = json.loads((FIXTURES / "truth.json").read_text())["documents"]


def printed(value: str | None) -> str | None:
    return None if value is None else f"{Decimal(value):,.2f}"


def _document(text: str) -> dict[str, Any]:
    if "ACCOUNT STATEMENT" in text:
        return next(d for d in DOCUMENTS if d["docType"] == "BANK_STATEMENT")
    for doc in DOCUMENTS:
        reference = doc.get("number") or doc.get("receiptNo")
        if reference and reference in text:
            return doc
    return next(d for d in DOCUMENTS if d["docType"] == "BANK_STATEMENT")


class RecordedDemoReader(FakeDocumentReader):
    def __init__(self) -> None:
        super().__init__(
            classification=lambda text: DocClassification(
                doc_type=_document(text)["docType"], confidence=0.99
            ),
            pages=_recorded_page,
        )

    async def read_invoice_page(self, image_png, chunks, *, page):
        d = _document(chunks)
        value = InvoicePageReading(
            page=page,
            invoice_number=d["number"],
            issuer_name=d["issuer"]["name"],
            buyer_name=d["billTo"]["name"],
            issuer_tax_id=d["issuer"]["taxId"],
            buyer_tax_id=d["billTo"]["taxId"],
            currency=d["currency"],
            issue_date_text=f"{date.fromisoformat(d['issueDate']):%d %b %Y}",
            due_date_text=f"{date.fromisoformat(d['dueDate']):%d %b %Y}",
            payment_bank_text=d["payTo"]["bankName"],
            payment_account_text=d["payTo"]["accountNumber"],
            lines=[
                InvoiceLineReading(
                    description=i["description"],
                    quantity_text=str(i["quantity"]),
                    unit_price_text=printed(i["unitPrice"]),
                    amount_text=printed(i["amount"]),
                )
                for i in d["lines"]
            ],
            subtotal_text=printed(d["subtotal"]),
            tax_text=printed(d["vat"]),
            total_text=printed(d["total"]),
            supply_kind="GOODS",
        )
        return ReaderCall(value, "fixture-reader", "invoice@recorded", 0, 0)

    async def read_receipt_page(self, image_png, chunks, *, page):
        d = _document(chunks)
        issued = datetime.fromisoformat(d["issuedAt"])
        value = ReceiptPageReading(
            page=page,
            merchant_name=d["merchant"]["name"].upper(),
            receipt_number=d["receiptNo"],
            date_text=f"{issued:%d/%m/%Y}",
            time_text=f"{issued:%H:%M}",
            currency=None,  # this till roll prints no currency
            total_text=printed(d["total"]),
            tax_text=printed(d["vat"]),
            payment_method_text=d["payment"],
            items=[
                ReceiptItemReading(
                    description=i["description"],
                    amount_text=printed(i["amount"]),
                )
                for i in d["items"]
            ],
        )
        return ReaderCall(value, "fixture-reader", "receipt@recorded", 0, 0)


def demo_deps():
    deps, _ = _deps()
    deps._reader = RecordedDemoReader()
    deps._bank_lines = FakeBankLineRepository()
    deps._receipts = fake_receipts()
    deps._findings = FakeFindingRepository()
    deps._decisions = FakeDecisionRepository()
    deps._matches = FakeMatchRepository()
    return deps
