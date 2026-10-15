"""Pure ledger parsing, layouts, signatures, shape masking and the column mapping a person
confirms once per layout (Spec 005, AC-005-10, AC-005-11, AC-005-12)."""

import csv
import hashlib
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from app.domain.profit_loss import LedgerRow

# The date formats a mapping may name (contracts LedgerMapping.dateFormat) and how to parse them.
DATE_FORMATS: dict[str, str] = {
    "DD/MM/YYYY": "%d/%m/%Y",
    "MM/DD/YYYY": "%m/%d/%Y",
    "YYYY-MM-DD": "%Y-%m-%d",
    "DD-MM-YYYY": "%d-%m-%Y",
    "DD.MM.YYYY": "%d.%m.%Y",
}

SignConvention = Literal["DEBIT_POSITIVE", "CREDIT_POSITIVE"]

# Header words per field, English and Indonesian (the packages the demo workspace exports from).
# The mapper looks at header words and value shapes only, never at the values themselves.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "date": (
        "date",
        "posting date",
        "trans date",
        "transaction date",
        "tanggal",
        "tgl",
        "tanggal posting",
    ),
    "description": (
        "description",
        "narration",
        "memo",
        "particulars",
        "details",
        "keterangan",
        "uraian",
        "deskripsi",
    ),
    "accountCode": (
        "account",
        "account code",
        "acct",
        "code",
        "gl account",
        "gl code",
        "account no",
        "kode akun",
        "kode",
        "no akun",
    ),
    "accountName": ("account name", "acct name", "gl name", "nama akun"),
    "reference": (
        "reference",
        "ref",
        "journal",
        "journal id",
        "voucher",
        "doc no",
        "no jurnal",
        "nomor jurnal",
    ),
    "debit": ("debit", "dr", "debet"),
    "credit": ("credit", "cr", "kredit"),
    "amount": ("amount", "net", "jumlah", "nominal", "nilai", "value"),
}
# The English layouts the parser already read without a person: these are confirmed by code.
STANDARD_HEADERS = frozenset(
    {
        "date",
        "posting date",
        "trans date",
        "account",
        "account code",
        "acct",
        "code",
        "account name",
        "acct name",
        "description",
        "narration",
        "reference",
        "ref",
        "journal",
        "journal id",
        "debit",
        "credit",
        "amount",
        "net",
    }
)


@dataclass(frozen=True)
class LedgerMapping:
    """Which column of the export holds each field (contracts LedgerMapping): either a debit and a
    credit column, or one signed amount column with its sign convention."""

    date: str = ""
    description: str = ""
    account_code: str = ""
    account_name: str | None = None
    reference: str | None = None
    debit: str | None = None
    credit: str | None = None
    amount: str | None = None
    sign_convention: SignConvention | None = None
    date_format: str = "DD/MM/YYYY"
    decimal_separator: str = "."

    def problems(self) -> list[str]:
        out = [
            f"{name}: choose the column"
            for name, value in (
                ("date", self.date),
                ("description", self.description),
                ("accountCode", self.account_code),
            )
            if not value
        ]
        two = bool(self.debit and self.credit)
        one = bool(self.amount)
        if two == one or (bool(self.debit) != bool(self.credit)):
            out.append("amounts: choose a debit and a credit column, or one amount column")
        if self.date_format not in DATE_FORMATS:
            out.append("dateFormat: unknown format")
        if self.decimal_separator not in (".", ","):
            out.append("decimalSeparator: must be '.' or ','")
        return out

    @property
    def complete(self) -> bool:
        return not self.problems()

    def columns(self) -> list[str]:
        return [
            c
            for c in (
                self.date,
                self.description,
                self.account_code,
                self.account_name,
                self.reference,
                self.debit,
                self.credit,
                self.amount,
            )
            if c
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "description": self.description,
            "accountCode": self.account_code,
            "accountName": self.account_name,
            "reference": self.reference,
            "debit": self.debit,
            "credit": self.credit,
            "amount": self.amount,
            "signConvention": self.sign_convention
            if not self.amount
            else (self.sign_convention or "DEBIT_POSITIVE"),
            "dateFormat": self.date_format,
            "decimalSeparator": self.decimal_separator,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LedgerMapping":
        def text(key: str) -> str | None:
            value = data.get(key)
            return str(value).strip() if value not in (None, "") else None

        amount = text("amount")
        sign = text("signConvention")
        return cls(
            date=text("date") or "",
            description=text("description") or "",
            account_code=text("accountCode") or "",
            account_name=text("accountName"),
            reference=text("reference"),
            debit=text("debit"),
            credit=text("credit"),
            amount=amount,
            sign_convention=(
                "DEBIT_POSITIVE"
                if amount and sign not in ("DEBIT_POSITIVE", "CREDIT_POSITIVE")
                else sign
            ),  # type: ignore[arg-type]
            date_format=text("dateFormat") or "DD/MM/YYYY",
            decimal_separator=text("decimalSeparator") or ".",
        )


@dataclass(frozen=True)
class LedgerParseResult:
    rows: list[LedgerRow]
    bad_rows: list[int] = field(default_factory=list)
    too_many_bad_rows: bool = False
    layout_signature: str = ""
    headers: list[str] = field(default_factory=list)


def compute_layout_signature(headers: list[str]) -> str:
    """AC-005-10: SHA-1 hex of normalized header row."""
    normalized = ",".join(h.strip().lower() for h in headers if h.strip())
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def mask_value_shapes(values: list[str]) -> list[str]:
    """AC-005-11: Mask values to character shapes (9 digits, A uppercase, a lowercase)."""
    masked = []
    for val in values:
        s = re.sub(r"\d", "9", val)
        s = re.sub(r"[A-Z]", "A", s)
        s = re.sub(r"[a-z]", "a", s)
        masked.append(s)
    return masked


def _parse_date(raw: str) -> date | None:
    val = raw.strip()
    if not val:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def _to_decimal(val: str | None) -> Decimal | None:
    if val is None or not val.strip():
        return None
    cleaned = val.strip().replace(",", "")
    try:
        return Decimal(cleaned)
    except Exception:
        return None


def _lines_of(content: str) -> list[str]:
    return [ln for ln in content.splitlines() if not ln.startswith("#") and ln.strip()]


def _dialect(lines: list[str]) -> type[csv.Dialect] | csv.Dialect:
    try:
        return csv.Sniffer().sniff("\n".join(lines[:5]), delimiters=",;\t|")
    except csv.Error:
        return csv.excel


def read_table(content: str) -> tuple[list[str], list[list[str]]]:
    """AC-005-10: the export as a table, delimiter sniffed; the header row and the data rows."""
    lines = _lines_of(content)
    if not lines:
        return [], []
    reader = csv.reader(lines, dialect=_dialect(lines))
    table = [[cell.strip() for cell in row] for row in reader]
    headers = [h for h in table[0]] if table else []
    width = len(headers)
    rows = [(row + [""] * width)[:width] for row in table[1:] if any(cell for cell in row)]
    return headers, rows


def _column(headers: list[str], rows: list[list[str]], name: str | None) -> list[str]:
    if not name or name not in headers:
        return []
    i = headers.index(name)
    return [r[i] for r in rows if i < len(r) and r[i]]


def sniff_date_format(values: list[str]) -> str:
    """The date format from the values' shapes (AC-005-11): day first unless a value says
    otherwise."""
    shapes = Counter(mask_value_shapes(values[:200]))
    shape = shapes.most_common(1)[0][0] if shapes else ""
    if shape == "9999-99-99":
        return "YYYY-MM-DD"
    if shape in ("99/99/9999", "9/9/9999", "99/9/9999", "9/99/9999"):
        firsts = [int(v.split("/")[0]) for v in values if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", v)]
        seconds = [int(v.split("/")[1]) for v in values if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", v)]
        if any(f > 12 for f in firsts):
            return "DD/MM/YYYY"
        if any(s > 12 for s in seconds):
            return "MM/DD/YYYY"
        return "DD/MM/YYYY"
    if shape == "99-99-9999":
        return "DD-MM-YYYY"
    if shape == "99.99.9999":
        return "DD.MM.YYYY"
    return "DD/MM/YYYY"


def sniff_decimal_separator(values: list[str]) -> str:
    """The decimal separator from the amounts' shapes: 1.250.000,00 uses a comma."""
    for v in values[:500]:
        if "," in v and "." in v:
            return "," if v.rfind(",") > v.rfind(".") else "."
    if any(re.match(r"^-?\d{1,3}(\.\d{3})+$", v) for v in values[:500]):
        return ","  # dots group thousands, so the decimals (when printed) use a comma
    if any(re.match(r"^-?\d+,\d{1,2}$", v) for v in values[:500]):
        return ","
    return "."


def propose_mapping(headers: list[str], rows: list[list[str]]) -> LedgerMapping:
    """AC-005-11: a mapping proposed from the header words and the value shapes only. Fields the
    header does not name stay empty for the person to choose."""
    lower = {h.lower().strip(): h for h in headers if h.strip()}

    def pick(field_name: str) -> str | None:
        for word in SYNONYMS[field_name]:
            if word in lower:
                return lower[word]
        return None

    debit, credit, amount = pick("debit"), pick("credit"), pick("amount")
    if debit and credit:
        amount = None
    elif amount:
        debit = credit = None
    date_col = pick("date")
    amount_values = [v for name in (debit, credit, amount) for v in _column(headers, rows, name)]
    return LedgerMapping(
        date=date_col or "",
        description=pick("description") or "",
        account_code=pick("accountCode") or "",
        account_name=pick("accountName"),
        reference=pick("reference"),
        debit=debit,
        credit=credit,
        amount=amount,
        sign_convention="DEBIT_POSITIVE" if amount else None,
        date_format=sniff_date_format(_column(headers, rows, date_col)),
        decimal_separator=sniff_decimal_separator(amount_values),
    )


def merge_model_proposal(proposal: LedgerMapping, model: Any, headers: list[str]) -> LedgerMapping:
    """AC-005-11: the model's answer fills only the fields code left empty, and only with columns
    that exist in the header; code keeps the date format and decimal separator it read from the
    shapes. The model never overrides a column code recognized."""
    by_lower = {h.lower().strip(): h for h in headers}

    def column(value: object) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None
        return by_lower.get(value.lower().strip())

    fields = {
        "date": "date",
        "description": "description",
        "account_code": "account_code",
        "account_name": "account_name",
        "reference": "reference",
        "debit": "debit",
        "credit": "credit",
        "amount": "amount",
    }
    taken = set(proposal.columns())
    updates: dict[str, Any] = {}
    for attr in fields:
        if getattr(proposal, attr):
            continue
        chosen = column(getattr(model, attr, None))
        if chosen and chosen not in taken:
            updates[attr] = chosen
            taken.add(chosen)
    debit = updates.get("debit", proposal.debit)
    credit = updates.get("credit", proposal.credit)
    amount = updates.get("amount", proposal.amount)
    if debit and credit:
        updates["amount"] = None
    elif amount:
        updates["debit"] = updates["credit"] = None
        if not proposal.sign_convention and getattr(model, "sign_convention", None) in (
            "DEBIT_POSITIVE",
            "CREDIT_POSITIVE",
        ):
            updates["sign_convention"] = model.sign_convention
        elif not proposal.sign_convention:
            updates["sign_convention"] = "DEBIT_POSITIVE"
    if not updates:
        return proposal
    return LedgerMapping(**{**proposal.__dict__, **updates})


def is_auto_confirmable(mapping: LedgerMapping, headers: list[str]) -> bool:
    """A complete proposal whose every mapped column has a standard English name is confirmed by
    code (the layouts the parser always read); anything else waits for a person."""
    return mapping.complete and all(
        c.lower().strip() in STANDARD_HEADERS for c in mapping.columns()
    )


def _parse_amount(raw: str | None, separator: str) -> Decimal | None:
    if raw is None or not raw.strip():
        return Decimal("0")
    text = raw.strip().replace(" ", "")
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    thousands = "." if separator == "," else ","
    text = text.replace(thousands, "").replace(separator, ".")
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    return -value if negative else value


def _row_with_mapping(
    row: dict[str, str],
    mapping: LedgerMapping,
    idx: int,
    doc_id: str,
    currency: str | None,
    posting_status: Literal["POSTED", "DRAFT", "UNKNOWN"],
) -> LedgerRow | str:
    """One data row through the mapping: the entry, or why the row cannot be read."""
    raw_date = row.get(mapping.date, "")
    try:
        day = datetime.strptime(raw_date, DATE_FORMATS[mapping.date_format]).date()
    except (ValueError, KeyError):
        return f"date '{raw_date}' is not {mapping.date_format}"
    account_code = row.get(mapping.account_code, "").strip()
    if not account_code:
        return "the account code is empty"
    if mapping.amount:
        value = _parse_amount(row.get(mapping.amount), mapping.decimal_separator)
        if value is None:
            return f"amount '{row.get(mapping.amount)}' is not a number"
        if mapping.sign_convention == "CREDIT_POSITIVE":
            value = -value
        debit, credit = (value, Decimal("0")) if value >= 0 else (Decimal("0"), -value)
    else:
        debit = _parse_amount(row.get(mapping.debit or ""), mapping.decimal_separator)
        credit = _parse_amount(row.get(mapping.credit or ""), mapping.decimal_separator)
        if debit is None or credit is None:
            return "the debit or credit is not a number"
        if debit > 0 and credit > 0:
            return "a row cannot be both a debit and a credit"
    return LedgerRow(
        entry_id=f"entry_{doc_id}_{idx}",
        doc_id=doc_id,
        row_number=idx,
        date=day,
        account_code=account_code,
        account_name=row.get(mapping.account_name or "", "") or row.get(mapping.description, ""),
        debit=debit,
        credit=credit,
        currency=currency,
        posting_status=posting_status,
        journal_id=(row.get(mapping.reference or "", "") or None),
        entry_kind="ACTIVITY",
        held_as_duplicate=False,
    )


def _parse_with_mapping(
    content: str,
    doc_id: str,
    mapping: LedgerMapping,
    currency: str | None,
    posting_status: Literal["POSTED", "DRAFT", "UNKNOWN"],
) -> LedgerParseResult:
    headers, rows = read_table(content)
    out: list[LedgerRow] = []
    bad: list[int] = []
    for idx, cells in enumerate(rows, start=1):
        entry = _row_with_mapping(
            dict(zip(headers, cells, strict=False)), mapping, idx, doc_id, currency, posting_status
        )
        if isinstance(entry, str):
            bad.append(idx)
        else:
            out.append(entry)
    total = len(out) + len(bad)
    return LedgerParseResult(
        rows=out,
        bad_rows=bad,
        too_many_bad_rows=(len(bad) / max(1, total)) > 0.02 if total else False,
        layout_signature=compute_layout_signature(headers),
        headers=headers,
    )


def sample_rows(
    content: str, mapping: LedgerMapping, *, currency: str | None = "IDR", limit: int = 5
) -> list[dict[str, Any]]:
    """AC-005-11: the first rows as the mapping reads them (contracts LedgerMappingView.sampleRows),
    so a person sees what a column choice does before confirming it."""
    headers, rows = read_table(content)
    out: list[dict[str, Any]] = []
    for idx, cells in enumerate(rows[:limit], start=1):
        entry = _row_with_mapping(
            dict(zip(headers, cells, strict=False)), mapping, idx, "preview", currency, "POSTED"
        )
        if isinstance(entry, str):
            out.append({"raw": cells, "parsed": None, "error": entry})
        else:
            out.append(
                {
                    "raw": cells,
                    "parsed": {
                        "date": entry.date.isoformat(),
                        "accountCode": entry.account_code,
                        "description": cells[headers.index(mapping.description)]
                        if mapping.description in headers
                        else "",
                        "debit": {"amount": f"{entry.debit:.2f}", "currency": currency or ""},
                        "credit": {"amount": f"{entry.credit:.2f}", "currency": currency or ""},
                    },
                    "error": None,
                }
            )
    return out


def parse_ledger_content(
    content: str,
    doc_id: str,
    *,
    currency: str | None = "IDR",
    posting_status: Literal["POSTED", "DRAFT", "UNKNOWN"] = "POSTED",
    mapping: LedgerMapping | None = None,
) -> LedgerParseResult:
    """Parse CSV text into LedgerRows: with a confirmed mapping, every column is read as the
    person said (AC-005-12); without one, the standard English layouts are recognized by name."""
    if mapping is not None:
        return _parse_with_mapping(content, doc_id, mapping, currency, posting_status)
    lines = _lines_of(content)
    if not lines:
        return LedgerParseResult(rows=[])

    reader = csv.DictReader(lines)
    raw_headers = list(reader.fieldnames or [])
    signature = compute_layout_signature(raw_headers)

    rows: list[LedgerRow] = []
    bad_rows: list[int] = []

    for idx, r in enumerate(reader, start=1):
        r_lower = {k.lower().strip(): (v.strip() if v else "") for k, v in r.items() if k}

        # Date parsing
        raw_date = (
            r_lower.get("date") or r_lower.get("posting date") or r_lower.get("trans date") or ""
        )
        d = _parse_date(raw_date)
        if d is None:
            bad_rows.append(idx)
            continue

        account_code = (
            r_lower.get("account")
            or r_lower.get("account code")
            or r_lower.get("acct")
            or r_lower.get("code")
            or ""
        )
        if not account_code:
            bad_rows.append(idx)
            continue

        account_name = (
            r_lower.get("account name")
            or r_lower.get("acct name")
            or r_lower.get("description")
            or r_lower.get("narration")
            or ""
        )
        journal_id = (
            r_lower.get("journal")
            or r_lower.get("journal id")
            or r_lower.get("ref")
            or r_lower.get("reference")
            or None
        )

        # Layout detection: debit & credit vs single signed amount
        has_debit_credit = "debit" in r_lower or "credit" in r_lower
        if has_debit_credit:
            debit_val = _to_decimal(r_lower.get("debit"))
            credit_val = _to_decimal(r_lower.get("credit"))

            # Check if values are invalid strings
            if r_lower.get("debit") and debit_val is None:
                bad_rows.append(idx)
                continue
            if r_lower.get("credit") and credit_val is None:
                bad_rows.append(idx)
                continue

            debit = debit_val or Decimal("0")
            credit = credit_val or Decimal("0")

            if debit > 0 and credit > 0:
                bad_rows.append(idx)
                continue
        else:
            # Single signed amount column (e.g. 'amount', 'net')
            raw_amt_str = r_lower.get("amount") or r_lower.get("net") or ""
            amt_val = _to_decimal(raw_amt_str)
            if amt_val is None:
                bad_rows.append(idx)
                continue
            if amt_val >= 0:
                debit = amt_val
                credit = Decimal("0")
            else:
                debit = Decimal("0")
                credit = abs(amt_val)

        entry_id = f"entry_{doc_id}_{idx}"
        rows.append(
            LedgerRow(
                entry_id=entry_id,
                doc_id=doc_id,
                row_number=idx,
                date=d,
                account_code=account_code,
                account_name=account_name,
                debit=debit,
                credit=credit,
                currency=currency,
                posting_status=posting_status,
                journal_id=journal_id,
                entry_kind="ACTIVITY",
                held_as_duplicate=False,
            )
        )

    total_candidates = len(rows) + len(bad_rows)
    too_many = (len(bad_rows) / max(1, total_candidates)) > 0.02 if total_candidates > 0 else False

    return LedgerParseResult(
        rows=rows,
        bad_rows=bad_rows,
        too_many_bad_rows=too_many,
        layout_signature=signature,
        headers=raw_headers,
    )
