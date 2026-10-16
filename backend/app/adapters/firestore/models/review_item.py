"""orgs/{orgId}/reviewItems/{itemId} as stored (docs/09 §3.11)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.adapters.firestore.models.base import FirestoreModel


class ReviewSubjectDoc(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")
    bank_line_ids: list[str] = Field(default_factory=list)
    invoice_ids: list[str] = Field(default_factory=list)
    receipt_ids: list[str] = Field(default_factory=list)
    ledger_entry_ids: list[str] = Field(default_factory=list)
    doc_ids: list[str] = Field(default_factory=list)
    match_id: str | None = None
    field: str | None = None


class ReviewCandidateDoc(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")
    match_id: str
    bank_line_ids: list[str] = Field(default_factory=list)
    invoice_ids: list[str] = Field(default_factory=list)
    receipt_ids: list[str] = Field(default_factory=list)
    score: str = "0"  # a decimal string
    reasons: list[str] = Field(default_factory=list)
    ai_rank: int | None = None  # spec 023: the model's order among the candidates (advice)
    ai_reason: str | None = None


class ReviewSuggestionDoc(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")
    candidates: list[ReviewCandidateDoc] = Field(default_factory=list)
    reading: dict[str, Any] | None = None
    doc_type: str | None = None
    confidence: str | None = None
    mapping: dict[str, Any] | None = None
    difference: str | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    ranked_by: str | None = None  # model@prompt that ordered the candidates


class ReviewResolutionDoc(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")
    action: str | None = None  # absent: the system closed it because its cause is gone
    note: str | None = None
    resolved_by: str
    resolved_at: datetime


class ReviewItemDoc(FirestoreModel):
    item_id: str
    kind: str
    month: str | None = None
    doc_id: str | None = None
    status: str = "OPEN"
    priority: int = 50
    title: str
    subject: ReviewSubjectDoc = Field(default_factory=ReviewSubjectDoc)
    suggestion: ReviewSuggestionDoc = Field(default_factory=ReviewSuggestionDoc)
    allowed_actions: list[str] = Field(default_factory=list)
    resolution: ReviewResolutionDoc | None = None
    key: str = ""  # the deterministic ID's input (docs/09 §4)
