"""Workspace, subscription and usage (docs/09 §3.1–§3.2, spec 013).

Domain shapes only; the Firestore documents and their schema versions live in
adapters/firestore/models/.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

EntityType = Literal["INDIVIDUAL", "COMPANY"]
SubscriptionStatus = Literal["TRIALING", "TRIAL_EXPIRED", "ACTIVE"]
Role = Literal["owner", "accountant", "reviewer", "viewer"]


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
