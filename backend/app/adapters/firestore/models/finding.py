"""orgs/{orgId}/findings/{findingId} as stored (docs/09 §3.12)."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.adapters.firestore.models.base import FirestoreModel


class EvidenceDoc(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )
    doc_id: str | None = None
    page: int | None = None
    bbox: dict[str, float] | None = None
    tx_id: str | None = None
    invoice_id: str | None = None
    receipt_id: str | None = None
    ledger_entry_id: str | None = None
    label: str | None = None


class FindingDoc(FirestoreModel):
    finding_id: str
    code: str
    category: str
    scope: str = "DOCUMENT"
    doc_id: str | None = None
    month: str | None = None
    severity: str
    severity_rank: int
    title: str
    facts: dict[str, str] = Field(default_factory=dict)
    explanation: str | None = None
    next_steps: list[str] = Field(default_factory=list)
    evidence: list[EvidenceDoc] = Field(default_factory=list)
    detected_by: str = "RULE"
    status: str = "OPEN"
    dismissal: dict[str, Any] | None = None
    last_seen_run_id: str | None = None
