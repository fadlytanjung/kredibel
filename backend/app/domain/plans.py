"""Plan catalog and entitlements (pure).

Normative references: contracts/plans.v1.yaml, ADR-011, spec 013 (AC-013-4, AC-013-5, AC-013-7,
AC-013-8). The file is read by `adapters/policy_files.py`; this module only validates and decides.
"""

from collections.abc import Mapping
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from pydantic.alias_generators import to_camel

from app.domain.models.workspace import Subscription, SubscriptionStatus

PlanStatus = Literal["AVAILABLE", "COMING_SOON"]


class _Contract(BaseModel):
    """camelCase in the file, snake_case in Python; unknown keys are a mistake (AC-013-5)."""

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid", frozen=True
    )


class Limits(_Contract):
    seats: int
    documents_per_month: int
    pages_per_document: int
    file_size_mb: int
    extracted_pages_per_month: int
    ledger_rows_per_file: int
    month_runs_per_day: int
    ai_spend_usd_per_month: Decimal
    assistant_questions_per_day: int

    @field_validator("ai_spend_usd_per_month", mode="before")
    @classmethod
    def _money_is_a_decimal_string(cls, value: Any) -> Any:
        # Money is never a float (non-negotiable 9); YAML 5.0 would silently become one.
        if not isinstance(value, str | Decimal):
            raise ValueError("aiSpendUsdPerMonth must be a decimal string such as \"5.00\"")
        return value


class Features(_Contract):
    extraction_mode: Literal["adaptive", "thorough"]
    escalation: bool
    escalation_pages_per_month: int
    finance_assistant: bool
    member_invites: bool
    month_sign_off: bool
    languages: list[str]


class Plan(_Contract):
    id: str
    label: str
    status: PlanStatus
    price_label: str | None = None
    trial_days: int | None = None
    after_trial: Literal["READ_ONLY"] | None = None
    limits: Limits | None = None
    features: Features | None = None
    highlights: list[str]

    @model_validator(mode="after")
    def _limits_only_on_available_plans(self) -> Self:
        if self.status == "COMING_SOON" and (self.limits or self.features):
            raise ValueError(f"COMING_SOON plan {self.id!r} must not define limits or features")
        if self.status == "AVAILABLE" and (self.limits is None or self.features is None):
            raise ValueError(f"AVAILABLE plan {self.id!r} needs limits and features")
        return self


class ComingSoonFeature(_Contract):
    id: str
    label: str
    description: str | None = None


class Language(_Contract):
    code: str
    label: str
    status: Literal["available", "coming_soon"]


class PlanCatalog(_Contract):
    version: Literal[1]
    id: str
    default_plan: str
    plans: list[Plan]
    coming_soon_features: list[ComingSoonFeature] = []
    languages: list[Language]

    @model_validator(mode="after")
    def _default_plan_is_assignable(self) -> Self:
        ids = [plan.id for plan in self.plans]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate plan ids in {ids}")
        default = next((plan for plan in self.plans if plan.id == self.default_plan), None)
        if default is None:
            raise ValueError(f"defaultPlan {self.default_plan!r} is not in plans")
        if default.status != "AVAILABLE":
            raise ValueError(f"defaultPlan {self.default_plan!r} must be AVAILABLE")
        return self

    def plan(self, plan_id: str) -> Plan:
        for plan in self.plans:
            if plan.id == plan_id:
                return plan
        raise KeyError(plan_id)

    def available_languages(self) -> list[str]:
        return [language.code for language in self.languages if language.status == "available"]


def parse_plans(data: Mapping[str, Any]) -> PlanCatalog:
    """Validate a plans file's content; raises pydantic.ValidationError on any violation."""
    return PlanCatalog.model_validate(data)


class LimitOverrides(_Contract):
    """Per-workspace limits that replace the plan's (the demo workspace, AC-013-4)."""

    seats: int | None = None
    documents_per_month: int | None = None
    pages_per_document: int | None = None
    file_size_mb: int | None = None
    extracted_pages_per_month: int | None = None
    ledger_rows_per_file: int | None = None
    month_runs_per_day: int | None = None
    ai_spend_usd_per_month: Decimal | None = None
    assistant_questions_per_day: int | None = None


def effective_limits(plan: Plan, overrides: Mapping[str, Any] | None) -> Limits:
    """The plan's limits with the workspace's overrides applied; unknown override keys raise."""
    if plan.limits is None:
        raise ValueError(f"plan {plan.id!r} has no limits")
    if not overrides:
        return plan.limits
    named = LimitOverrides.model_validate(overrides).model_dump(exclude_none=True)
    return plan.limits.model_copy(update=named)


def subscription_status(sub: Subscription, now: datetime) -> SubscriptionStatus:
    """Derived from the clock, so a stored TRIALING never outlives trialEndsAt (AC-013-8)."""
    if sub.status == "ACTIVE":
        return "ACTIVE"
    if sub.trial_ends_at is not None and now >= sub.trial_ends_at:
        return "TRIAL_EXPIRED"
    return "TRIALING"


def trial_days_left(sub: Subscription, now: datetime) -> int:
    """Whole days left, a started day counting as one ("Free trial: 1 day left" until the end)."""
    if sub.trial_ends_at is None or now >= sub.trial_ends_at:
        return 0
    remaining = sub.trial_ends_at - now
    return -(-remaining // timedelta(days=1))
