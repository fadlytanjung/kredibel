"""Persistence models for workspaces (docs/09 §3.1, §3.3, §3.4, §3.16, §3.18)."""

from datetime import datetime
from typing import Any

from pydantic import Field

from app.adapters.firestore.models.base import FirestoreModel
from app.domain.models.workspace import Currency, EntityType


class OrgDoc(FirestoreModel):
    """orgs/{orgId}"""

    org_id: str
    name: str
    entity_type: EntityType
    profile: dict[str, Any]
    country: str
    timezone: str
    currency: Currency
    default_language: str
    subscription: dict[str, Any]
    learning: dict[str, Any] = Field(default_factory=lambda: {"shareVerifiedLabels": False})
    # docs/09 §3.1, §3.8: layout signature → the confirmed column mapping (spec 005, additive).
    ledger_mappings: dict[str, Any] = Field(default_factory=dict)
    counts: dict[str, Any] = Field(default_factory=dict)
    # Spec 024 (additive): the person's goal, and per month {month, moneyInMinor?, moneyOutMinor?}.
    goal: str | None = None
    expectations: list[dict[str, Any]] = Field(default_factory=list)
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
    # Spec 021: when this person finished or skipped the guided tour (additive; none: not yet).
    tour_seen_at: datetime | None = None


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


class UsageMonthDoc(FirestoreModel):
    """orgs/{orgId}/usageMonthly/{yyyy-mm} (UTC month)."""

    org_id: str
    month: str
    documents_uploaded: int = 0
    pages_reserved: int = 0
    pages_read: int = 0
    pages_cached: int = 0
    ocr_pages: int = 0
    parser_pages: int = 0
    # Money is a decimal string in Firestore JSON-like fields, never a float (docs/09 §2).
    ai_spend_usd: str = "0"


class UsageDayDoc(FirestoreModel):
    """orgs/{orgId}/usage/{yyyy-mm-dd} (UTC day)."""

    org_id: str
    day: str
    month_runs: int = 0
    assistant_questions: int = 0
