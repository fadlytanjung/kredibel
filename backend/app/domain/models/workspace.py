"""Workspace, subscription and usage (docs/09 §3.1–§3.2, spec 013).

Domain shapes only; the Firestore documents and their schema versions live in
adapters/firestore/models/.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

EntityType = Literal["INDIVIDUAL", "COMPANY"]
SubscriptionStatus = Literal["TRIALING", "TRIAL_EXPIRED", "ACTIVE"]
Role = Literal["owner", "accountant", "reviewer", "viewer"]
Currency = Literal["IDR", "MYR", "SGD", "JPY", "USD"]


class DomainModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid", frozen=True
    )


class Subscription(DomainModel):
    plan_id: str
    status: SubscriptionStatus
    trial_started_at: datetime | None = None
    trial_ends_at: datetime | None = None
    # Set by the server (bootstrap) only, never through the API (spec 013 edge cases).
    limit_overrides: dict[str, int | str] | None = None


class UsageMonth(DomainModel):
    """orgs/{orgId}/usageMonthly/{yyyy-mm}; months are UTC (spec 013 edge cases)."""

    month: str
    documents_uploaded: int = 0
    pages_reserved: int = 0
    pages_read: int = 0
    pages_cached: int = 0
    ocr_pages: int = 0
    parser_pages: int = 0
    ai_spend_usd: Decimal = Decimal("0")


class UsageDay(DomainModel):
    """orgs/{orgId}/usage/{yyyy-mm-dd}."""

    day: str
    month_runs: int = 0
    assistant_questions: int = 0


class Address(DomainModel):
    line1: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, max_length=100)


class Profile(DomainModel):
    legal_name: str | None = Field(default=None, max_length=200)
    trading_name: str | None = Field(default=None, max_length=200)
    legal_form: (
        Literal["LIMITED_COMPANY", "PARTNERSHIP", "SOLE_PROPRIETOR", "COOPERATIVE", "OTHER"] | None
    ) = None
    industry: str | None = Field(default=None, max_length=100)
    tax_id_masked: str | None = None
    address: Address | None = None
    aliases: list[str] = Field(default_factory=list, max_length=10)
    accounting_framework: Literal["IFRS", "US_GAAP"] = "IFRS"


class BankAccountCreate(DomainModel):
    """The full number is accepted once; only its mask and keyed hash are stored."""

    bank_name: str = Field(min_length=1, max_length=100)
    account_number: str = Field(pattern=r"^[0-9 -]{6,30}$")
    holder_name: str = Field(min_length=1, max_length=200)
    nickname: str | None = Field(default=None, max_length=50)
    ledger_account_code: str | None = Field(default=None, max_length=30)


class WorkspaceCreate(DomainModel):
    """POST /api/workspaces (contracts/openapi.yaml WorkspaceCreate, AC-013-2)."""

    name: str = Field(min_length=2, max_length=100)
    # Kredibel is for businesses (AC-013-2): a new workspace is always a company.
    entity_type: Literal["COMPANY"] = "COMPANY"
    profile: Profile | None = None
    tax_id: str | None = Field(default=None, max_length=30)
    country: Literal["ID"] = "ID"
    timezone: str = Field(min_length=1, max_length=64)
    # The books' currency (ADR-020); the onboarding form suggests one from the time zone.
    currency: Currency = "IDR"
    bank_accounts: list[BankAccountCreate] = Field(default_factory=list, max_length=5)


class BankAccount(DomainModel):
    account_id: str
    bank_name: str
    account_masked: str
    holder_name: str
    nickname: str | None = None
    source: Literal["DECLARED", "DETECTED"] = "DECLARED"
    ledger_account_code: str | None = None
    first_month: str | None = None
    last_month: str | None = None


class Workspace(DomainModel):
    """orgs/{orgId} as the services see it."""

    org_id: str
    name: str
    entity_type: EntityType
    profile: Profile
    country: str
    timezone: str
    currency: Currency
    default_language: str
    subscription: Subscription
    share_verified_labels: bool = False
    # docs/09 §3.8: per file layout signature, the column mapping a person confirmed (spec 005).
    ledger_mappings: dict[str, dict[str, Any]] = Field(default_factory=dict)
    created_by: str
    created_at: datetime


class LearningSettings(DomainModel):
    share_verified_labels: bool = False


class WorkspaceUpdate(DomainModel):
    """PATCH /api/workspace. The entity type is fixed, so it is not a field (AC-013-14)."""

    name: str | None = Field(default=None, min_length=2, max_length=100)
    profile: Profile | None = None
    tax_id: str | None = Field(default=None, max_length=30)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    # No currency: it is fixed after onboarding (ADR-020); support changes it with a script.
    default_language: str | None = Field(default=None, min_length=2, max_length=8)
    learning: LearningSettings | None = None


class BankAccountUpdate(DomainModel):
    nickname: str | None = Field(default=None, max_length=50)
    # null clears the mapping
    ledger_account_code: str | None = Field(default=None, max_length=30)
