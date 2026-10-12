"""orgs/{orgId}/invoices/{invoiceId} and receipts/{receiptId} as stored (docs/09 §3.7)."""

from typing import Any

from pydantic import Field

from app.adapters.firestore.models.base import FirestoreModel


def _unpaid() -> dict[str, Any]:
    return {"state": "UNPAID", "paidMinor": 0, "matchIds": []}


class InvoiceLineDoc(FirestoreModel):
    description: str
    qty: str | None = None  # a decimal string: quantities are not money
    unit_price_minor: int | None = None
    amount_minor: int | None = None


class PayToDoc(FirestoreModel):
    bank_name: str | None = None
    account_masked: str | None = None


class InvoiceDoc(FirestoreModel):
    invoice_id: str
    doc_id: str
    kind: str
    number: str | None = None
    issuer_name: str | None = None
    issuer_tax_id: str | None = None  # masked
    buyer_name: str | None = None
    buyer_tax_id: str | None = None  # masked
    issue_date: str | None = None
    due_date: str | None = None
    month: str | None = None
    currency: str | None = None
    subtotal_minor: int | None = None
    tax_minor: int | None = None
    total_minor: int | None = None
    pay_to: PayToDoc = Field(default_factory=PayToDoc)
    lines: list[InvoiceLineDoc] = Field(default_factory=list)
    supply_kind: str | None = None
    pages: list[int] = Field(default_factory=list)
    consensus: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    payment: dict[str, Any] = Field(default_factory=_unpaid)
    held_as_duplicate: bool = False
    counterparty_id: str | None = None


class ReceiptItemDoc(FirestoreModel):
    description: str
    amount_minor: int | None = None


class ReceiptDoc(FirestoreModel):
    receipt_id: str
    doc_id: str
    merchant_name: str | None = None
    merchant_tax_id: str | None = None  # masked
    number: str | None = None
    date: str | None = None
    time: str | None = None
    month: str | None = None
    currency: str | None = None
    total_minor: int | None = None
    tax_minor: int | None = None
    payment_method: str = "UNKNOWN"
    items: list[ReceiptItemDoc] = Field(default_factory=list)
    pages: list[int] = Field(default_factory=list)
    consensus: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    payment: dict[str, Any] = Field(default_factory=_unpaid)
    held_as_duplicate: bool = False
