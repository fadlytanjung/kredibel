"""orgs/{orgId}/suggestions/{suggestionId} as stored (docs/09 §3.14)."""

from datetime import datetime
from typing import Any

from pydantic import Field

from app.adapters.firestore.models.base import FirestoreModel


class SuggestionDoc(FirestoreModel):
    suggestion_id: str
    field: str
    value: dict[str, Any] = Field(default_factory=dict)
    display: str = ""
    confidence: str = "MEDIUM"
    basis: str = ""
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "PENDING"
    conflict_with: str | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None
