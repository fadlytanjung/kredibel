"""The books as data (plan 002): generated first, rendered second, so files and truth agree.

Money is `Decimal` with two places everywhere; amounts are whole rupiah written as `1250000.00`.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def whole(value: Decimal) -> Decimal:
    """Rounded to a whole rupiah, still written with two places."""
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP).quantize(CENT)


def fmt(value: Decimal) -> str:
    """English number format of the documents: 1,250,000.00 (docs/18 §3.1)."""
    return f"{value:,.2f}"


Flow = Literal[
    "sale",
    "deposit",
    "supplier",
    "card",
    "payroll",
    "rent",
    "utility",
    "vat",
    "loan",
    "drawing",
    "fee",
]


@dataclass
class BankRow:
    key: str
    date: date
    description: str
    flow: Flow
    category: str
    debit: Decimal | None = None
    credit: Decimal | None = None
    party: str | None = None
    row_index: int = 0
    balance: Decimal = ZERO
    risk_tags: list[str] = field(default_factory=list)
    # Documents this line pays or is paid by (keys), filled by books.py.
    documents: list[str] = field(default_factory=list)
    invoice_refs: list[str] = field(default_factory=list)
    in_ledger: bool = True

    @property
    def amount(self) -> Decimal:
        return self.credit if self.credit is not None else (self.debit or ZERO)

    @property
    def direction(self) -> Literal["in", "out"]:
        return "in" if self.credit is not None else "out"


@dataclass
class StatementData:
    month: str  # yyyy-mm
    period_start: date
    period_end: date
    opening: Decimal
    rows: list[BankRow]
    created_at: datetime  # local time UTC+7, the day after the period end at 02:00
    account_number: str
    holder: str
    holder_address: list[str]
    bank_name: str
    branch: str

    @property
    def closing(self) -> Decimal:
        return self.rows[-1].balance if self.rows else self.opening

    @property
    def total_debits(self) -> Decimal:
        return sum((r.debit for r in self.rows if r.debit is not None), ZERO)

    @property
    def total_credits(self) -> Decimal:
        return sum((r.credit for r in self.rows if r.credit is not None), ZERO)


@dataclass(frozen=True)
class Party:
    name: str
    address: tuple[str, ...] = ()
    tax_id: str | None = None


@dataclass(frozen=True)
class PayTo:
    bank_name: str
    account_number: str
    holder: str


@dataclass(frozen=True)
class Line:
    description: str
    quantity: int
    unit_price: Decimal

    @property
    def amount(self) -> Decimal:
        return money(self.unit_price * self.quantity)


@dataclass
class InvoiceData:
    key: str  # file name without extension: inv-sales-2026-03-01
    kind: Literal["SALES", "PURCHASE"]
    number: str
    issue_date: date
    due_date: date
    issuer: Party
    bill_to: Party
    lines: list[Line]
    vat_rate: Decimal
    pay_to: PayTo
    layout: str
    terms_days: int

    @property
    def subtotal(self) -> Decimal:
        return sum((line.amount for line in self.lines), ZERO)

    @property
    def vat(self) -> Decimal:
        return whole(self.subtotal * self.vat_rate)

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.vat

    @property
    def party(self) -> str:
        """The other side: the client of a sales invoice, the supplier of a purchase invoice."""
        return self.bill_to.name if self.kind == "SALES" else self.issuer.name

    @property
    def file(self) -> str:
        return f"{self.key}.pdf"


@dataclass
class ReceiptData:
    key: str  # receipt-2026-03-02
    merchant: Party
    issued_at: datetime
    items: list[Line]
    vat_rate: Decimal
    payment: str  # CASH, DEBIT CARD ••4821, QRIS
    form: Literal["jpeg", "pdf"]
    expense_account: str
    receipt_no: str

    @property
    def subtotal(self) -> Decimal:
        return sum((item.amount for item in self.items), ZERO)

    @property
    def vat(self) -> Decimal:
        return whole(self.subtotal * self.vat_rate)

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.vat

    @property
    def date(self) -> date:
        return self.issued_at.date()

    @property
    def file(self) -> str:
        return f"{self.key}.{'jpg' if self.form == 'jpeg' else 'pdf'}"


@dataclass
class LedgerRow:
    date: date
    journal: str
    account: str
    account_name: str
    description: str
    reference: str
    debit: Decimal | None = None
    credit: Decimal | None = None
    key: str = ""  # lg#<line in the CSV>, set when the ledger is numbered
    bank_key: str | None = None  # the bank line this 1110 entry mirrors
    document_key: str | None = None  # the invoice or receipt this entry books

    @property
    def amount(self) -> Decimal:
        return self.debit if self.debit is not None else (self.credit or ZERO)


MatchKind = Literal[
    "BANK_SALES_INVOICE",
    "BANK_PURCHASE_INVOICE",
    "BANK_RECEIPT",
    "BANK_LEDGER",
    "DOCUMENT_LEDGER",
]


Expect = Literal["AUTO", "PROPOSED"]


@dataclass
class IntendedMatch:
    month: str
    kind: MatchKind
    bank: list[str]
    documents: list[str]
    ledger: list[str]
    expect: "Expect"
    reasons: list[str]
    score: Decimal
    # For a PROPOSED match: the document the money really belongs to (the first of `documents`).
    note: str = ""


@dataclass
class Books:
    seed: int
    statements: dict[str, StatementData]
    sales: list[InvoiceData]
    purchases: list[InvoiceData]
    receipts: list[ReceiptData]
    ledger: list[LedgerRow]
    matches: list[IntendedMatch] = field(default_factory=list)

    @property
    def bank_rows(self) -> list[BankRow]:
        return [row for st in self.statements.values() for row in st.rows]

    @property
    def invoices(self) -> list[InvoiceData]:
        return [*self.sales, *self.purchases]
