"""Pure parsing of general-ledger CSV exports into domain LedgerRow instances (spec 018)."""

import csv
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from app.domain.profit_loss import LedgerRow


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


def _to_decimal(val: str | None) -> Decimal:
    if not val:
        return Decimal("0")
    cleaned = val.strip().replace(",", "")
    try:
        return Decimal(cleaned)
    except Exception:
        return Decimal("0")


def parse_ledger_csv(
    content: str,
    doc_id: str,
    *,
    currency: str | None = "IDR",
    posting_status: Literal["POSTED", "DRAFT", "UNKNOWN"] = "POSTED",
) -> list[LedgerRow]:
    """Parse CSV text into LedgerRows. Ignores comment lines starting with #."""
    lines = [ln for ln in content.splitlines() if not ln.startswith("#") and ln.strip()]
    if not lines:
        return []

    reader = csv.DictReader(lines)
    rows: list[LedgerRow] = []
    for idx, r in enumerate(reader, start=1):
        # Match case-insensitively across possible column naming
        r_lower = {k.lower().strip(): (v.strip() if v else "") for k, v in r.items() if k}
        raw_date = r_lower.get("date") or ""
        d = _parse_date(raw_date)
        if d is None:
            continue

        account_code = (
            r_lower.get("account")
            or r_lower.get("account code")
            or r_lower.get("code")
            or ""
        )
        account_name = r_lower.get("account name") or r_lower.get("description") or ""
        journal_id = (
            r_lower.get("journal")
            or r_lower.get("journal id")
            or r_lower.get("ref")
            or r_lower.get("reference")
            or None
        )
        debit = _to_decimal(r_lower.get("debit"))
        credit = _to_decimal(r_lower.get("credit"))

        if debit > 0 and credit > 0:
            # Cannot have both on a single row in our LedgerRow model
            continue

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
    return rows
