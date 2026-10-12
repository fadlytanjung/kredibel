"""Invoices and receipts as read from a document (docs/09 §3.7), with their grounding."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Literal

PaymentMethod = Literal["CASH", "CARD", "TRANSFER", "UNKNOWN"]
SupplyKind = Literal["GOODS", "SERVICES", "MIXED"]


@dataclass
class InvoiceLine:
    description: str
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None


@dataclass
class Invoice:
    invoice_id: str
    doc_id: str
    kind: Literal["SALES", "PURCHASE"]
    number: str | None
    issuer_name: str | None
    buyer_name: str | None
    issue_date: date | None
    month: str | None  # of the issue date
    total: Decimal | None
    currency: str | None = None
    issuer_tax_id: str | None = None
    buyer_tax_id: str | None = None
    due_date: date | None = None
    subtotal: Decimal | None = None
    tax: Decimal | None = None
    pay_to_bank: str | None = None
    pay_to_masked: str | None = None  # the account printed for payment, masked
    supply_kind: SupplyKind | None = None
    lines: list[InvoiceLine] = field(default_factory=list)
    pages: list[int] = field(default_factory=list)
    consensus: dict[str, dict[str, Any]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    evidence: dict[str, Any] | None = None  # written by the month run (ADR-025)


@dataclass
class ReceiptItem:
    description: str
    amount: Decimal | None = None


@dataclass
class Receipt:
    receipt_id: str
    doc_id: str
    merchant_name: str | None
    date: date | None
    month: str | None
    total: Decimal | None
    currency: str | None = None
    merchant_tax_id: str | None = None
    number: str | None = None
    time: str | None = None
    tax: Decimal | None = None
    payment_method: PaymentMethod = "UNKNOWN"
    items: list[ReceiptItem] = field(default_factory=list)
    pages: list[int] = field(default_factory=list)
    consensus: dict[str, dict[str, Any]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    evidence: dict[str, Any] | None = None  # written by the month run (ADR-025)
