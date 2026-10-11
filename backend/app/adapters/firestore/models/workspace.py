"""Persistence models for workspaces (docs/09 §3.1, §3.3, §3.4, §3.16, §3.18)."""

from datetime import datetime
from typing import Any

from pydantic import Field

from app.adapters.firestore.models.base import FirestoreModel
from app.domain.models.workspace import EntityType


class OrgDoc(FirestoreModel):
    """orgs/{orgId}"""

    org_id: str
    name: str
    entity_type: EntityType
    profile: dict[str, Any]
    country: str
    timezone: str
    currency: str
    default_language: str
    subscription: dict[str, Any]
    learning: dict[str, Any] = Field(default_factory=lambda: {"shareVerifiedLabels": False})
    counts: dict[str, Any] = Field(default_factory=dict)
    created_by: str
    created_at: datetime


class MemberDoc(FirestoreModel):
    """orgs/{orgId}/members/{uid}; authorization uses the custom claim, not this document."""

    uid: str
    org_id: str
    email: str | None = None
    display_name: str | None = None
    role: str
    language: str = "en"
    created_at: datetime


class BankAccountDoc(FirestoreModel):
    """orgs/{orgId}/bankAccounts/{accountId}; the number only as a mask."""

    account_id: str
    org_id: str
    bank_name: str
    holder_name: str
    account_masked: str
    nickname: str | None = None
    source: str = "DECLARED"
    ledger_account_code: str | None = None
    first_month: str | None = None
    last_month: str | None = None


class AccountHashDoc(FirestoreModel):
    """orgPrivate/{orgId}/accountHashes/{accountId}; server only."""

    org_id: str
    account_id: str
    hash: str


class SignupDoc(FirestoreModel):
    """system/signup"""

    workspaces_created: int = 0


class SignupUserDoc(FirestoreModel):
    """system/signup/users/{uid}: the user's one workspace."""

    uid: str
    org_id: str
    role: str
    created_at: datetime


class EventDoc(FirestoreModel):
    """orgs/{orgId}/events/{eventId}; append-only."""

    event_id: str
    org_id: str
    type: str
    actor_uid: str
    actor_role: str
    at: datetime
    subject: dict[str, str]
    details: dict[str, Any] = Field(default_factory=dict)
