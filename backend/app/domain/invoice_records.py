"""Grounded invoice and receipt pages become records (docs/07 §5.2, §6.2; docs/09 §3.7). Pure.

A PDF can hold several invoices or receipts: a page with a different printed number starts the
next one, and a page without a number continues the current one. Header values come from the first
page that has them and totals from the last. Every value is looked for on its own page; tax IDs and
account numbers are stored masked.
"""

import re
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, Protocol

from rapidfuzz import fuzz

from app.core.ids import content_id

from .accounts import account_digits, mask_account, mask_tax_id
from .models.invoice import Invoice, InvoiceLine, Receipt, ReceiptItem, SupplyKind
from .normalize import AmountStyle, detect_amount_style, parse_amount, parse_date, payment_method
from .reading import (
    InvoicePageReading,
    ReceiptPageReading,
    currency_code,
)
from .verify import BBox, FieldCheck, ItemCheck, ValueKind, Word, check_items, check_value

_SAME_NAME = 85  # rapidfuzz token_set_ratio at which a printed name is the workspace's own


@dataclass
class RecordsResult[T]:
    records: list[T]
    agreed: int
    compared: int
    page_agreement: dict[int, float]
    months: list[str]
    notes: list[str] = field(default_factory=list)

    @property
    def agreement(self) -> float:
        return 1.0 if self.compared == 0 else self.agreed / self.compared


class _Tally:
    def __init__(self) -> None:
        self.agreed = 0
        self.compared = 0
        self.pages: dict[int, list[int]] = {}

    def count(self, check: FieldCheck | None, page: int) -> None:
        if check is None:
            return
        self.compared += 1
        hit = int(check.status == "AGREED")
        self.agreed += hit
        agreed, compared = self.pages.setdefault(page, [0, 0])
        self.pages[page] = [agreed + hit, compared + 1]

    def page_agreement(self) -> dict[int, float]:
        return {p: (a / c if c else 1.0) for p, (a, c) in self.pages.items()}


def _bbox(box: BBox | None) -> dict[str, float] | None:
    return None if box is None else {"x0": box.x0, "y0": box.y0, "x1": box.x1, "y1": box.y1}


def _consensus(check: FieldCheck, page: int) -> dict[str, Any]:
    return {
        "status": check.status,
        "bbox": _bbox(check.bbox),
        "page": page,
        "raw": {"GEMINI": check.ai, "TEXT_LAYER": check.witness},
    }


def _fold(text: str | None) -> str:
    folded = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", folded).strip().upper()


def is_own_name(printed: str | None, own_names: Sequence[str]) -> bool:
    """The workspace's legal or trading name, allowing for spacing, case and suffix differences."""
    name = _fold(printed)
    return bool(name) and any(
        fuzz.token_set_ratio(name, _fold(own)) >= _SAME_NAME for own in own_names if own
    )


def invoice_kind(
    issuer: str | None, buyer: str | None, own_names: Sequence[str], classified: str
) -> Literal["SALES", "PURCHASE"]:
    """Sales or purchase is decided in code from the workspace's names (AC-005-1); the classifier's
    guess only breaks a tie."""
    if is_own_name(issuer, own_names) and not is_own_name(buyer, own_names):
        return "SALES"
    if is_own_name(buyer, own_names):
        return "PURCHASE"
    return "SALES" if classified == "SALES_INVOICE" else "PURCHASE"


def document_type_of(kinds: Sequence[str], classified: str) -> str:
    """The document's type from the kinds decided in code: one kind for every invoice it holds
    wins over the classifier's guess; a mixed or empty document keeps the guess."""
    if kinds and all(kind == "PURCHASE" for kind in kinds):
        return "PURCHASE_INVOICE"
    if kinds and all(kind == "SALES" for kind in kinds):
        return "SALES_INVOICE"
    return classified


def _group[P: (InvoicePageReading, ReceiptPageReading)](
    pages: list[P], number: Callable[[P], str | None]
) -> list[list[P]]:
    groups: list[list[P]] = []
    current: str | None = None
    for page in sorted(pages, key=lambda p: p.page):
        printed = re.sub(r"\s+", "", number(page) or "").upper() or None
        if not groups or (printed and current and printed != current):
            groups.append([page])
        else:
            groups[-1].append(page)
        current = printed or current
    return groups


class _Paged(Protocol):
    @property
    def page(self) -> int: ...


def _first[P: _Paged](pages: list[P], value: Callable[[P], str | None]) -> tuple[str | None, int]:
    """A header value from the first page that prints it, with that page."""
    for p in pages:
        if v := value(p):
            return v, p.page
    return None, pages[0].page


def _last[P: _Paged](pages: list[P], value: Callable[[P], str | None]) -> tuple[str | None, int]:
    """A total from the last page that prints it, with that page."""
    return _first(list(reversed(pages)), value)


class _Fields:
    """Checks each value on its own page and keeps the consensus by field name."""

    def __init__(self, words: dict[int, list[Word]], tally: _Tally) -> None:
        self.words = words
        self.tally = tally
        self.consensus: dict[str, dict[str, Any]] = {}

    def check(self, name: str, value: str | None, kind: ValueKind, page: int) -> str | None:
        result = check_value(value, kind, self.words.get(page, []))
        self.tally.count(result, page)
        if result is not None:
            self.consensus[name] = _consensus(result, page)
        return value

    def first[P: _Paged](
        self, name: str, pages: list[P], value: Callable[[P], str | None], kind: ValueKind
    ) -> str | None:
        printed, page = _first(pages, value)
        return self.check(name, printed, kind, page)

    def last[P: _Paged](
        self, name: str, pages: list[P], value: Callable[[P], str | None]
    ) -> str | None:
        printed, page = _last(pages, lambda p: printed_amount(value(p)))
        return self.check(name, printed, "amount", page)

    def items(self, prefix: str, page: int, checks: list[ItemCheck]) -> None:
        """Count each item's description and amount, keeping the amount's consensus by position."""
        start = sum(1 for k in self.consensus if k.startswith(prefix) and k.endswith(".amount"))
        for offset, check in enumerate(checks):
            self.tally.count(check.description, page)
            self.tally.count(check.amount, page)
            if check.amount is not None:
                self.consensus[f"{prefix}.{start + offset}.amount"] = _consensus(check.amount, page)


def printed_amount(text: str | None) -> str | None:
    """An amount the page prints as a word ("Included", "FREE") is no amount: not compared."""
    return text if text and re.search(r"\d", text) else None


def _amount(text: str | None, style: AmountStyle, notes: list[str]) -> Decimal | None:
    parsed = parse_amount(printed_amount(text), style)
    if parsed.note:
        notes.append(parsed.note)
    return parsed.value


def _date(text: str | None, notes: list[str]) -> date | None:
    parsed = parse_date(text)
    if parsed.note:
        notes.append(parsed.note)
    return parsed.value


def _quantity(text: str | None, style: AmountStyle = "EN") -> Decimal | None:
    """A quantity as printed, in the document's number style ("1,692" is 1692 on an English-style
    invoice, "1.692" on an Indonesian one); a separator is grouping only before groups of exactly
    three digits, otherwise it is the decimal point. A unit after the number is dropped."""
    match = re.match(r"^\s*(\d[\d.,]*)", text or "")
    if not match:
        return None
    raw = match[1].rstrip(".,")
    group, decimal = (",", ".") if style == "EN" else (".", ",")
    if re.fullmatch(rf"\d{{1,3}}(?:\{group}\d{{3}})+(?:\{decimal}\d+)?", raw):
        raw = raw.replace(group, "")
    try:
        return Decimal(raw.replace(",", "."))
    except InvalidOperation:
        return None


def _style(texts: list[str | None]) -> AmountStyle:
    return detect_amount_style([t for t in texts if t])


def build_invoices(
    doc_id: str,
    pages: list[InvoicePageReading],
    words: dict[int, list[Word]],
    *,
    classified: str,
    own_names: Sequence[str],
) -> RecordsResult[Invoice]:
    tally = _Tally()
    style = _style(
        [t for p in pages for t in (p.subtotal_text, p.tax_text, p.total_text)]
        + [ln.amount_text for p in pages for ln in p.lines]
    )
    invoices: list[Invoice] = []
    all_notes: list[str] = []
    for index, group in enumerate(_group(pages, lambda p: p.invoice_number)):
        fields = _Fields(words, tally)
        notes: list[str] = []

        number = fields.first("number", group, lambda p: p.invoice_number, "text")
        issuer = fields.first("issuerName", group, lambda p: p.issuer_name, "text")
        buyer = fields.first("buyerName", group, lambda p: p.buyer_name, "text")
        issued = _date(fields.first("issueDate", group, lambda p: p.issue_date_text, "date"), notes)
        due = _date(fields.first("dueDate", group, lambda p: p.due_date_text, "date"), notes)
        account = fields.first("payTo", group, lambda p: p.payment_account_text, "text")
        issuer_tax, _ = _first(group, lambda p: p.issuer_tax_id)
        buyer_tax, _ = _first(group, lambda p: p.buyer_tax_id)
        bank, _ = _first(group, lambda p: p.payment_bank_text)
        currency, _ = _first(group, lambda p: p.currency)
        supply: SupplyKind | None = next((p.supply_kind for p in group if p.supply_kind), None)
        subtotal = _amount(fields.last("subtotal", group, lambda p: p.subtotal_text), style, notes)
        tax = _amount(fields.last("tax", group, lambda p: p.tax_text), style, notes)
        total = _amount(fields.last("total", group, lambda p: p.total_text), style, notes)

        lines: list[InvoiceLine] = []
        for p in group:
            items = [(ln.description, printed_amount(ln.amount_text)) for ln in p.lines]
            fields.items("lines", p.page, check_items(items, words.get(p.page, [])))
            lines += [
                InvoiceLine(
                    description=ln.description,
                    quantity=_quantity(ln.quantity_text, style),
                    unit_price=_amount(ln.unit_price_text, style, notes),
                    amount=_amount(ln.amount_text, style, notes),
                )
                for ln in p.lines
            ]
        if (
            subtotal is not None
            and tax is not None
            and total is not None
            and subtotal + tax != total
        ):
            notes.append("subtotal plus tax differs from the printed total")
        digits = account_digits(account or "")
        invoices.append(
            Invoice(
                invoice_id=content_id("inv", doc_id, str(index)),
                doc_id=doc_id,
                kind=invoice_kind(issuer, buyer, own_names, classified),
                number=number,
                issuer_name=issuer,
                buyer_name=buyer,
                issue_date=issued,
                month=issued.strftime("%Y-%m") if issued else None,
                total=total,
                currency=currency_code(currency),
                issuer_tax_id=mask_tax_id(issuer_tax) if issuer_tax else None,
                buyer_tax_id=mask_tax_id(buyer_tax) if buyer_tax else None,
                due_date=due,
                subtotal=subtotal,
                tax=tax,
                pay_to_bank=bank,
                pay_to_masked=mask_account(digits) if len(digits) >= 4 else None,
                supply_kind=supply,
                lines=lines,
                pages=[p.page for p in group],
                consensus=_masked(fields.consensus),
                notes=notes,
            )
        )
        all_notes += notes
    months = sorted({i.month for i in invoices if i.month})
    return RecordsResult(
        invoices, tally.agreed, tally.compared, tally.page_agreement(), months, all_notes
    )


def build_receipts(
    doc_id: str, pages: list[ReceiptPageReading], words: dict[int, list[Word]]
) -> RecordsResult[Receipt]:
    tally = _Tally()
    style = _style(
        [t for p in pages for t in (p.tax_text, p.total_text)]
        + [i.amount_text for p in pages for i in p.items]
    )
    receipts: list[Receipt] = []
    all_notes: list[str] = []
    for index, group in enumerate(_group(pages, lambda p: p.receipt_number)):
        fields = _Fields(words, tally)
        notes: list[str] = []
        merchant = fields.first("merchantName", group, lambda p: p.merchant_name, "text")
        number = fields.first("number", group, lambda p: p.receipt_number, "text")
        date_text = fields.first("date", group, lambda p: p.date_text, "date")
        total_text = fields.last("total", group, lambda p: p.total_text)
        tax_text = fields.last("tax", group, lambda p: p.tax_text)
        method, _ = _first(group, lambda p: p.payment_method_text)
        currency, _ = _first(group, lambda p: p.currency)
        tax_id, _ = _first(group, lambda p: p.merchant_tax_id)
        time_text, _ = _first(group, lambda p: p.time_text)

        items: list[ReceiptItem] = []
        for p in group:
            pairs = [(i.description, printed_amount(i.amount_text)) for i in p.items]
            fields.items("items", p.page, check_items(pairs, words.get(p.page, [])))
            items += [
                ReceiptItem(i.description, _amount(i.amount_text, style, notes)) for i in p.items
            ]
        issued = _date(date_text, notes)
        receipts.append(
            Receipt(
                receipt_id=content_id("rcp", doc_id, str(index)),
                doc_id=doc_id,
                merchant_name=merchant,
                date=issued,
                month=issued.strftime("%Y-%m") if issued else None,
                total=_amount(total_text, style, notes),
                currency=currency_code(currency),
                merchant_tax_id=mask_tax_id(tax_id) if tax_id else None,
                number=number,
                time=time_text,
                tax=_amount(tax_text, style, notes),
                payment_method=payment_method(method),
                items=items,
                pages=[p.page for p in group],
                consensus=fields.consensus,
                notes=notes,
            )
        )
        all_notes += notes
    months = sorted({r.month for r in receipts if r.month})
    return RecordsResult(
        receipts, tally.agreed, tally.compared, tally.page_agreement(), months, all_notes
    )


def _masked(consensus: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """The printed payment account stays out of storage; only its last four digits remain."""
    pay_to = consensus.get("payTo")
    if pay_to is None:
        return consensus
    raw = {
        source: (mask_account(account_digits(v)) if v and len(account_digits(v)) >= 4 else v)
        for source, v in pay_to["raw"].items()
    }
    return {**consensus, "payTo": {**pay_to, "raw": raw}}
