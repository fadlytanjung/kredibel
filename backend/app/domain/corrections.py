"""A person corrects a value read from an invoice, receipt, or bank line (spec 009, T009-03a/b).

Pure: the record and the text in, the corrected record out. The reading stays in `consensus`, the
field is listed in `corrected_fields`, and a corrected date moves the record to its month.
"""

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.domain.errors import ValidationProblem
from app.domain.models.bank_line import BankLine
from app.domain.models.invoice import Invoice, Receipt

CORRECTABLE = {
    Invoice: ("total", "issueDate"),
    Receipt: ("total", "date"),
    BankLine: ("amount", "date"),
}
_ATTRIBUTE = {
    "total": "total",
    "issueDate": "issue_date",
    "date": "date",
    "amount": "amount",
}


def _amount(text: str) -> Decimal:
    try:
        value = Decimal(text.strip().replace(",", ""))
    except InvalidOperation:
        raise ValidationProblem("value", "Write the amount as digits, e.g. 476976.00.") from None
    if not value.is_finite() or value <= 0:
        raise ValidationProblem("value", "The amount must be more than zero.")
    return value.quantize(Decimal("0.01"))


def _signed_amount(text: str, original: Decimal) -> Decimal:
    try:
        value = Decimal(text.strip().replace(",", ""))
    except InvalidOperation:
        raise ValidationProblem("value", "Write the amount as digits, e.g. 476976.00.") from None
    if not value.is_finite() or value == 0:
        raise ValidationProblem("value", "The amount must be non-zero.")
    # If the original line was a debit (negative) and user entered an unsigned positive number,
    # preserve the debit sign.
    if original < 0 and value > 0 and not text.strip().startswith("+"):
        value = -value
    return value.quantize(Decimal("0.01"))


def _day(text: str) -> date:
    try:
        return date.fromisoformat(text.strip())
    except ValueError:
        raise ValidationProblem("value", "Write the date as YYYY-MM-DD.") from None


def correct_record[R: (Invoice, Receipt, BankLine)](
    record: R, field: str, text: str, *, by: str, at: datetime
) -> R:
    if field not in CORRECTABLE[type(record)]:
        raise ValidationProblem(
            "field", f"Only {' or '.join(CORRECTABLE[type(record)])} can be corrected."
        )
    changes: dict[str, object] = {}
    if field == "total":
        changes["total"] = _amount(text)
    elif field == "amount":
        assert isinstance(record, BankLine)
        changes["amount"] = _signed_amount(text, record.amount)
    else:
        day = _day(text)
        changes[_ATTRIBUTE[field]] = day
        changes["month"] = f"{day:%Y-%m}"
    fields = [*record.corrected_fields, *([field] if field not in record.corrected_fields else [])]
    return replace(record, **changes, corrected_fields=fields, corrected_by=by, corrected_at=at)


def _id(record: Invoice | Receipt | BankLine) -> str:
    if isinstance(record, Invoice):
        return record.invoice_id
    if isinstance(record, Receipt):
        return record.receipt_id
    return record.tx_id


def keep_corrections[R: (Invoice, Receipt, BankLine)](fresh: list[R], stored: list[R]) -> list[R]:
    """A document read again keeps what a person corrected (a decision is never undone by a
    re-run): each corrected field, its month, and who corrected it, by record ID."""
    corrected = {_id(s): s for s in stored if s.corrected_fields}
    out: list[R] = []
    for record in fresh:
        before = corrected.get(_id(record))
        if before is None:
            out.append(record)
            continue
        kept: dict[str, object] = {}
        for name in before.corrected_fields:
            attribute = _ATTRIBUTE[name]
            kept[attribute] = getattr(before, attribute)
            if name != "total" and name != "amount":
                kept["month"] = before.month
        out.append(
            replace(
                record,
                **kept,
                corrected_fields=list(before.corrected_fields),
                corrected_by=before.corrected_by,
                corrected_at=before.corrected_at,
            )
        )
    return out
