"""Additive v1 reporting shapes, conservative legacy defaults (docs/09 §3.8)."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.adapters.firestore.models.base import FirestoreModel


class LedgerEntryDoc(FirestoreModel):
    org_id: str
    entry_id: str
    doc_id: str
    row_number: int = Field(ge=1)
    date: str
    account_code: str
    account_name: str = ""
    debit_minor: int = Field(ge=0)
    credit_minor: int = Field(ge=0)
    currency: str | None = None
    posting_status: Literal["POSTED", "DRAFT", "UNKNOWN"] = "UNKNOWN"
    journal_id: str | None = None
    entry_kind: Literal["ACTIVITY", "OPENING", "CLOSING"] = "ACTIVITY"
    held_as_duplicate: bool = False


class AccountClassificationDoc(FirestoreModel):
    org_id: str
    account_code: str
    pnl_line: str
    subledger: str
    confirmed_by: str
    confirmed_at: datetime
