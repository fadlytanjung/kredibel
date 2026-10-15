from datetime import datetime
from typing import Any

from pydantic import Field

from app.adapters.firestore.models.base import FirestoreModel


class BankLineDoc(FirestoreModel):
    tx_id: str
    doc_id: str
    account_id: str | None = None
    page: int
    row_index: int
    date: str  # yyyy-mm-dd
    month: str
    description: str
    counterparty_name: str | None = None
    amount_minor: int
    balance_minor: int | None = None
    source: str = "AI"
    consensus: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)
    category: str | None = None
    cashflow_class: str = "UNCLASSIFIED"
    risk_tags: list[str] = Field(default_factory=list)
    categorized_by: str = "NONE"
    category_confidence: str | None = None
    held_as_duplicate: bool = False
    match: dict[str, Any] = Field(default_factory=lambda: {"state": "UNMATCHED", "matchIds": []})
    support: str | None = None
    corrected_fields: list[str] = Field(default_factory=list)
    corrected_by: str | None = None
    corrected_at: datetime | None = None

