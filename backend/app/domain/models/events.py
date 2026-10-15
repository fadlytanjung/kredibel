"""Append-only audit events (docs/09 §3.16): IDs, actor and small details, never content."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

EventType = Literal[
    "WORKSPACE_CREATED",
    "BANK_ACCOUNT_ADDED",
    "PROFILE_UPDATED",
    "LABEL_VERIFIED",
    "LABEL_CORRECTED",
    "DOCUMENT_UPLOADED",
    "DUPLICATE_RECORDED",
    "DOCUMENT_REMOVED",
    "CURRENCY_CHANGED",
    "DECISION_RECORDED",
    "DECISION_WITHDRAWN",
    "CATEGORY_CHANGED",
    "ACCOUNT_CLASSIFIED",
    "MATCH_CREATED",
    "MATCH_CONFIRMED",
    "MATCH_REJECTED",
    "DUPLICATE_CONFIRMED",
    "DUPLICATE_REJECTED",
    "REVIEW_ITEM_RESOLVED",
    "VALUE_CORRECTED",
    "LEDGER_MAPPING_CONFIRMED",
    "SUGGESTION_ACCEPTED",
    "SUGGESTION_REJECTED",
]


class AuditEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    type: EventType
    actor_uid: str
    actor_role: str
    at: datetime
    subject: dict[str, str]
    details: dict[str, str | int | bool] = {}
