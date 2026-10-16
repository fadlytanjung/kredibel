"""orgs/{orgId}/labels/{labelId} and orgs/{orgId}/workspaceRules/{ruleId} as stored
(docs/09 §3.19 and §3.20)."""

from datetime import datetime
from typing import Any

from pydantic import Field

from app.adapters.firestore.models.base import FirestoreModel


class LabelDoc(FirestoreModel):
    label_id: str
    task: str
    subject: dict[str, Any] = Field(default_factory=dict)
    month: str | None = None
    ai: dict[str, Any] = Field(default_factory=dict)
    final: dict[str, Any] = Field(default_factory=dict)
    status: str = "AI_PROPOSED"
    needs_check: bool = False
    framework: str | None = None
    cashflow_class: str | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None
    note: str | None = None
    ai_disagrees_with_person: bool = False
    dataset: dict[str, Any] = Field(default_factory=dict)
    extraction_url: str | None = None
    page_image_url: str | None = None
    example_text: str | None = None


class WorkspaceRuleDoc(FirestoreModel):
    rule_id: str
    counterparty_key: str
    direction: str
    category: str
    source_label_id: str
    created_by: str
    created_at: datetime
    active: bool = True
