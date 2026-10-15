"""orgs/{orgId}/matches/{matchId} as stored (docs/09 §3.10)."""

from datetime import datetime

from pydantic import Field

from app.adapters.firestore.models.base import FirestoreModel


class MatchDoc(FirestoreModel):
    match_id: str
    month: str
    kind: str
    status: str
    method: str | None = None
    bank_line_ids: list[str] = Field(default_factory=list)
    invoice_ids: list[str] = Field(default_factory=list)
    receipt_ids: list[str] = Field(default_factory=list)
    ledger_entry_ids: list[str] = Field(default_factory=list)
    amount_minor: int = 0
    amount_difference_minor: int = 0
    score: str = "0"
    reasons: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    requires_review: bool = False
    created_by: str = "system"
    created_at: datetime | None = None
    run_id: str | None = None
