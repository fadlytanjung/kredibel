"""Pure ledger parsing, layouts, signatures, and shape masking (Spec 005, AC-005-10, AC-005-12)."""

import csv
import hashlib
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from app.domain.profit_loss import LedgerRow


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


def parse_ledger_content(
    content: str,
    doc_id: str,
    *,
    currency: str | None = "IDR",
    posting_status: Literal["POSTED", "DRAFT", "UNKNOWN"] = "POSTED",
) -> LedgerParseResult:
    """Parse CSV text into LedgerRows with layout detection and bad row tracking."""
    lines = [ln for ln in content.splitlines() if not ln.startswith("#") and ln.strip()]
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
            r_lower.get("date")
            or r_lower.get("posting date")
            or r_lower.get("trans date")
            or ""
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
    too_many = (
        (len(bad_rows) / max(1, total_candidates)) > 0.02
        if total_candidates > 0
        else False
    )

    return LedgerParseResult(
        rows=rows,
        bad_rows=bad_rows,
        too_many_bad_rows=too_many,
        layout_signature=signature,
        headers=raw_headers,
    )
