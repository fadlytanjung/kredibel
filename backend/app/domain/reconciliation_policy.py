"""Validated reconciliation policy; no file I/O or fallback thresholds (docs/08 §6)."""

from decimal import Decimal
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

Share = Annotated[Decimal, Field(ge=0, le=1, allow_inf_nan=False)]
Nonnegative = Annotated[Decimal, Field(ge=0, allow_inf_nan=False)]
Days = Annotated[int, Field(ge=0, strict=True)]


class _Part(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, frozen=True, extra="forbid")


class AmountTolerance(_Part):
    min_minor: int = Field(ge=0)  # retained for the legacy IDR synthetic generator
    minimum_by_currency: dict[str, Nonnegative] = Field(min_length=1)
    share: Share

    @model_validator(mode="after")
    def valid_currency_codes(self) -> Self:
        if any(
            len(c) != 3 or not c.isascii() or not c.isupper() or not c.isalpha()
            for c in self.minimum_by_currency
        ):
            raise ValueError("currency floors require uppercase three-letter codes")
        return self


class Windows(_Part):
    invoice_before_issue_days: Days
    default_terms_days: Days
    grace_days: Days
    receipt_days: Days
    ledger_days: Days
    neighbour_months: Days


class Weights(_Part):
    amount: Share
    party: Share
    reference: Share
    date: Share

    @model_validator(mode="after")
    def sum_to_one(self) -> Self:
        if self.amount + self.party + self.reference + self.date != 1:
            raise ValueError("reconciliation weights must sum to one")
        return self


class Thresholds(_Part):
    auto_confirm_score: Share
    ambiguity_margin: Share
    propose_score: Share
    party_min_score_for_split: Share
    max_split_parts: int = Field(ge=2, strict=True)
    max_group_parts: int = Field(ge=2, strict=True)
    max_auto_group_parts: int = Field(ge=2, strict=True)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.auto_confirm_score <= self.propose_score or self.ambiguity_margin <= 0:
            raise ValueError("automatic matches require a higher score and a positive margin")
        return self


class LedgerCash(_Part):
    rival_days: Days
    min_party: Share


class Expectations(_Part):
    tolerance: Share


class ReasonThresholds(_Part):
    party: Share
    date: Share


class ReconciliationPolicy(_Part):
    version: int
    id: str
    amount_tolerance: AmountTolerance
    max_withholding: Share
    withholding_rates: list[Share]
    fee_allowance: dict[str, Nonnegative]
    net_of_tax_amount_score: Share
    windows: Windows
    weights: Weights
    thresholds: Thresholds
    reason_thresholds: ReasonThresholds
    ledger: dict[str, Any]
    ledger_cash: LedgerCash
    review_items: dict[str, Any]
    expectations: Expectations

    @model_validator(mode="after")
    def identity_needed_for_auto(self) -> Self:
        if self.weights.amount + self.weights.date >= self.thresholds.auto_confirm_score:
            raise ValueError("amount and date alone must not reach the automatic threshold")
        if self.ledger_cash.rival_days < self.windows.ledger_days:
            raise ValueError("a rival is looked for at least as far as a booking may be")
        return self

    def tolerance(self, total: Decimal, workspace_currency: str) -> Decimal | None:
        minimum = self.amount_tolerance.minimum_by_currency.get(workspace_currency)
        if minimum is None:
            return None
        return max(minimum, abs(total) * self.amount_tolerance.share)
