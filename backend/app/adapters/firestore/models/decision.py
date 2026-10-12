"""orgs/{orgId}/decisions/{decisionId} as stored (docs/09 §3.21)."""

from datetime import datetime

from pydantic import Field

from app.adapters.firestore.models.base import FirestoreModel


class DecisionDoc(FirestoreModel):
    decision_id: str
    kind: str
    status: str = "ACTIVE"
    doc_id: str | None = None
    invoice_id: str | None = None
    receipt_id: str | None = None
    tx_id: str | None = None
    record_id: str | None = None  # invoice, receipt or bank line: one field to query by
    amount_minor: int | None = None
    currency: str | None = None
    paid_on: str | None = None
    method: str | None = None
    reason: str | None = None
    printed_currency: str | None = None
    months: list[str] = Field(default_factory=list)
    decided_by: str
    decided_at: datetime
    withdrawn_by: str | None = None
    withdrawn_at: datetime | None = None
