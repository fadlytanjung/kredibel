"""What the reader returns and how grounded pages become records (docs/07 §5.2, §7, §8; ADR-023).

The schemas are the reader's response schemas (strings as printed, chunk citations);
`build_statement` is pure: grounded pages in, bank lines and statement metadata out.
"""

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.ids import content_id

from .layout import Chunk
from .models.bank_line import BankLine
from .normalize import (
    AmountStyle,
    Parsed,
    detect_amount_style,
    extract_counterparty,
    parse_amount,
    parse_date,
    parse_period,
)
from .verify import AiRow, BBox, FieldCheck, ground_statement_page

# ---------------------------------------------------------------------------- reader schemas


class DocClassification(BaseModel):
    doc_type: Literal[
        "BANK_STATEMENT", "SALES_INVOICE", "PURCHASE_INVOICE", "RECEIPT", "LEDGER_EXPORT", "OTHER"
    ]
    confidence: float = Field(ge=0, le=1)
    language: str = "en"
    issuer_name: str | None = None
    counterparty_name: str | None = None
    period_hint: str | None = None
    currency: str | None = None
    reasons: list[str] = Field(default_factory=list)


class LedgerMappingProposal(BaseModel):
    """map_ledger_columns.md (AC-005-11): which header holds each field, decided from the header
    words and the value shapes only. Code validates every column against the header."""

    date: str | None = None
    description: str | None = None
    account_code: str | None = None
    account_name: str | None = None
    reference: str | None = None
    debit: str | None = None
    credit: str | None = None
    amount: str | None = None
    sign_convention: Literal["DEBIT_POSITIVE", "CREDIT_POSITIVE"] | None = None
    date_format: (
        Literal["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD", "DD-MM-YYYY", "DD.MM.YYYY"] | None
    ) = None
    decimal_separator: Literal[".", ","] | None = None
    confidence: float = Field(ge=0, le=1, default=0)
    reasons: list[str] = Field(default_factory=list)


PageType = Literal[
    "STATEMENT_SUMMARY",
    "STATEMENT_TRANSACTIONS",
    "TERMS_OR_COVER",
    "INVOICE",
    "RECEIPT",
    "LEDGER",
    "OTHER",
]


class StatementHeader(BaseModel):
    bank_name: str | None = None
    account_holder: str | None = None
    account_number: str | None = None
    holder_address: str | None = None
    currency: str | None = None
    period_start_text: str | None = None
    period_end_text: str | None = None
    opening_balance_text: str | None = None
    column_order: list[str] = Field(default_factory=list)


class StatementTotals(BaseModel):
    total_debits_text: str | None = None
    total_credits_text: str | None = None
    closing_balance_text: str | None = None


class StatementRowReading(BaseModel):
    row_on_page: int
    date_text: str = ""
    description: str = ""
    debit_text: str | None = None
    credit_text: str | None = None
    balance_text: str | None = None
    chunk_ids: list[str] = Field(default_factory=list)
    differs_from_text: list[str] = Field(default_factory=list)


class StatementPageReading(BaseModel):
    page: int
    header: StatementHeader | None = None
    rows: list[StatementRowReading] = Field(default_factory=list)
    totals: StatementTotals | None = None
    # What the page is (spec 016, PAGE_TYPE labels); absent from readings cached before it.
    page_type: PageType | None = None
    page_type_confidence: float | None = Field(default=None, ge=0, le=1)


# ---------------------------------------------------------------------------- statements

_CURRENCIES = {
    "RM": "MYR",
    "MYR": "MYR",
    "IDR": "IDR",
    "RP": "IDR",
    "SGD": "SGD",
    "S$": "SGD",
    "JPY": "JPY",
    "¥": "JPY",
    "USD": "USD",
    "US$": "USD",
    "$": "USD",
}
_OPENING = re.compile(r"(?i)\b(B/?F|BROUGHT\s*FORWARD|OPENING|BAKI\s*AWAL|SALDO\s*AWAL)")
_CLOSING = re.compile(r"(?i)\b(C/?F|CARRIED\s*FORWARD|CLOSING|BAKI\s*AKHIR|SALDO\s*AKHIR)")


class InvoiceLineReading(BaseModel):
    description: str
    quantity_text: str | None = None
    unit_price_text: str | None = None
    amount_text: str | None = None
    chunk_ids: list[str] = Field(default_factory=list)


class InvoicePageReading(BaseModel):
    """One page of an invoice, values as printed. A PDF can hold several invoices: a page with a
    different invoice number starts the next one."""

    page: int
    invoice_number: str | None = None
    issuer_name: str | None = None
    issuer_tax_id: str | None = None
    buyer_name: str | None = None
    buyer_tax_id: str | None = None
    issue_date_text: str | None = None
    due_date_text: str | None = None
    currency: str | None = None
    payment_bank_text: str | None = None
    payment_account_text: str | None = None
    lines: list[InvoiceLineReading] = Field(default_factory=list)
    subtotal_text: str | None = None
    tax_text: str | None = None
    total_text: str | None = None
    supply_kind: Literal["GOODS", "SERVICES", "MIXED"] | None = None
    # What the page is (spec 016, PAGE_TYPE labels); absent from readings cached before it.
    page_type: PageType | None = None
    page_type_confidence: float | None = Field(default=None, ge=0, le=1)
    differs_from_text: list[str] = Field(default_factory=list)


class ReceiptItemReading(BaseModel):
    description: str
    amount_text: str | None = None
    chunk_ids: list[str] = Field(default_factory=list)


class ReceiptPageReading(BaseModel):
    page: int
    merchant_name: str | None = None
    merchant_tax_id: str | None = None
    receipt_number: str | None = None
    date_text: str | None = None
    time_text: str | None = None
    currency: str | None = None
    items: list[ReceiptItemReading] = Field(default_factory=list)
    tax_text: str | None = None
    total_text: str | None = None
    payment_method_text: str | None = None
    # What the page is (spec 016, PAGE_TYPE labels); absent from readings cached before it.
    page_type: PageType | None = None
    page_type_confidence: float | None = Field(default=None, ge=0, le=1)
    differs_from_text: list[str] = Field(default_factory=list)


class TransactionItem(BaseModel):
    """A bank line as the categorizer sees it (docs/08 §4.1, txn_categorizer)."""

    id: int
    description: str
    direction: Literal["in", "out"]
    amount: str


class CategoryChoice(BaseModel):
    id: int
    category: str
    confidence: float = Field(ge=0, le=1)
    counterparty_name: str | None = None
    counterparty_kind: Literal["PERSON", "BUSINESS", "GOVERNMENT", "BANK", "UNKNOWN"] | None = None


class CategorizeResult(BaseModel):
    items: list[CategoryChoice] = Field(default_factory=list)


@dataclass
class StatementMeta:
    bank_name: str | None
    account_holder: str | None
    account_masked: str | None
    account_digits: str | None  # for the keyed hash in orgPrivate; never stored in clear
    holder_address: str | None
    currency: str | None
    period_start: date | None
    period_end: date | None
    opening: Decimal | None
    closing: Decimal | None


@dataclass
class StatementResult:
    lines: list[BankLine]
    meta: StatementMeta
    months: list[str]
    fields_agreed: int
    fields_compared: int
    page_agreement: dict[int, float]
    notes: list[str] = field(default_factory=list)

    @property
    def agreement(self) -> float:
        return 1.0 if not self.fields_compared else self.fields_agreed / self.fields_compared


def currency_code(printed: str | None) -> str | None:
    if not printed:
        return None
    key = re.sub(r"[\s()]", "", printed).upper()
    return _CURRENCIES.get(key) or _CURRENCIES.get(key.replace("RINGGIT", "RM"))


def _bbox(box: BBox | None) -> dict[str, float] | None:
    return None if box is None else {"x0": box.x0, "y0": box.y0, "x1": box.x1, "y1": box.y1}


def _consensus(check: FieldCheck, page: int) -> dict[str, Any]:
    return {
        "status": check.status,
        "bbox": _bbox(check.bbox),
        "page": page,
        "raw": {"GEMINI": check.ai, "TEXT_LAYER": check.witness},
    }


def _chosen(check: FieldCheck | None) -> str | None:
    """The value used: the shared one when agreed, the printed one when they conflict and the page
    shows one, else what the only source said (docs/07 §7)."""
    if check is None:
        return None
    if check.status == "CONFLICT" and check.witness:
        return check.witness
    return check.ai if check.ai is not None else check.witness


def _amounts(pages: list[StatementPageReading]) -> list[str]:
    out: list[str] = []
    for p in pages:
        out += [v for r in p.rows for v in (r.debit_text, r.credit_text, r.balance_text) if v]
    return out


def build_statement(
    doc_id: str, pages: list[StatementPageReading], chunks: dict[int, list[Chunk]]
) -> StatementResult:
    header = next((p.header for p in pages if p.header), None) or StatementHeader()
    totals = next((p.totals for p in reversed(pages) if p.totals), None) or StatementTotals()
    style: AmountStyle = detect_amount_style(_amounts(pages))
    period = parse_period(header.period_start_text, header.period_end_text)

    verified = []
    agreed = compared = 0
    page_agreement: dict[int, float] = {}
    for reading in sorted(pages, key=lambda p: p.page):
        rows = [
            AiRow(
                r.row_on_page,
                r.date_text,
                r.description,
                r.debit_text,
                r.credit_text,
                r.balance_text,
                tuple(r.chunk_ids),
                tuple(r.differs_from_text),
            )
            for r in reading.rows
        ]
        result = ground_statement_page(rows, chunks.get(reading.page, []), page=reading.page)
        if result.carry_over and verified:
            previous = verified[-1].fields.get("description")
            if previous and previous.ai:
                previous.ai = f"{previous.ai}\n{result.carry_over}"
        verified += result.rows
        agreed += result.agreed
        compared += result.compared
        page_agreement[reading.page] = result.agreement

    lines: list[BankLine] = []
    notes: list[str] = []
    opening_row: Decimal | None = None
    closing_row: Decimal | None = None
    for index, row in enumerate(verified):
        f = row.fields
        description = _chosen(f.get("description")) or ""
        balance = parse_amount(_chosen(f.get("balance")), style).value
        debit = parse_amount(_chosen(f.get("debit")), style).value
        credit = parse_amount(_chosen(f.get("credit")), style).value
        if debit is None and credit is None:
            if _OPENING.search(description) and opening_row is None:
                opening_row = balance
            elif _CLOSING.search(description):
                closing_row = balance
            elif balance is None or not description:
                notes.append(f"row {index}: no amount")
            continue
        if debit is not None and credit is not None:
            notes.append(f"row {index}: both debit and credit")
            continue
        when = parse_date(_chosen(f.get("date")), period=period)
        if when.value is None and not _chosen(f.get("date")) and lines:
            # Printed without a date: statements that print the date once per day (docs/07 §7).
            when = Parsed(lines[-1].date, "date of the row above")
        if when.value is None:
            notes.append(f"row {index}: {when.note or 'no date'}")
            continue
        amount = credit if credit is not None else -abs(debit or Decimal(0))
        amount_check = f.get("credit") if credit is not None else f.get("debit")
        consensus = {
            name: _consensus(check, row.page)
            for name, check in (
                ("date", f.get("date")),
                ("description", f.get("description")),
                ("amount", amount_check),
                ("balance", f.get("balance")),
            )
            if check is not None
        }
        lines.append(
            BankLine(
                tx_id=content_id("tx", doc_id, str(index)),
                doc_id=doc_id,
                page=row.page,
                row_index=index,
                date=when.value,
                month=f"{when.value:%Y-%m}",
                description=description,
                amount=amount,
                balance=balance,
                counterparty_name=extract_counterparty(description),
                source=row.source,
                consensus=consensus,
                notes=[*row.notes, *([when.note] if when.note else [])],
                chunk_ids=row.chunk_ids,
            )
        )

    digits = re.sub(r"\D", "", header.account_number or "")
    opening = parse_amount(header.opening_balance_text, style).value
    if opening is None:
        opening = opening_row
    if opening is None and lines and lines[0].balance is not None:
        opening = lines[0].balance - lines[0].amount
    closing = parse_amount(totals.closing_balance_text, style).value
    if closing is None:
        closing = closing_row if closing_row is not None else (lines[-1].balance if lines else None)
    meta = StatementMeta(
        bank_name=header.bank_name,
        account_holder=header.account_holder,
        account_masked=f"••••{digits[-4:]}" if len(digits) >= 4 else None,
        account_digits=digits or None,
        holder_address=header.holder_address,
        currency=currency_code(header.currency),
        period_start=period[0] if period else None,
        period_end=period[1] if period else None,
        opening=opening,
        closing=closing,
    )
    months = sorted({ln.month for ln in lines})
    return StatementResult(lines, meta, months, agreed, compared, page_agreement, notes)
