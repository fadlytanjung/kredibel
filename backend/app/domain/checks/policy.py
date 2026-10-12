"""contracts/policy/forensics.v1.yaml as the checks read it (docs/08 §2–§3). Pure."""

import re
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _Model(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")


class Arithmetic(_Model):
    balance_tolerance_minor: int = 100
    invoice_line_tolerance_minor: int = 100


class FontAnomaly(_Model):
    majority_share: Decimal = Decimal("0.90")
    min_values_on_page: int = 5


class Structure(_Model):
    editor_producer_patterns: list[str] = Field(default_factory=list)
    modified_after_creation_minutes: int = 10
    font_anomaly: FontAnomaly = Field(default_factory=FontAnomaly)


class Extraction(_Model):
    min_agreement: Decimal = Decimal("0.90")
    min_type_confidence: Decimal = Decimal("0.60")


class Duplicates(_Model):
    statement_overlap_min_days: int = 1
    invoice_issuer_min_score: int = 90
    receipt_total_tolerance_minor: int = 100
    p_hash_max_distance: int = Field(default=8, alias="pHashMaxDistance")


class CrossDocument(_Model):
    holder_name_min_score: int = 80


class Verdict(_Model):
    integrity_categories: list[str] = Field(
        default_factory=lambda: ["SCREENING", "EXTRACTION", "ARITHMETIC", "STRUCTURE", "VISUAL"]
    )
    tampered_codes: list[str] = Field(
        default_factory=lambda: [
            "A01_RUNNING_BALANCE_BREAK",
            "A02_OPENING_CLOSING_MISMATCH",
            "M03_MULTIPLE_REVISIONS",
        ]
    )
    suspicious_medium_count: int = 2


class ForensicsPolicy(_Model):
    id: str = "forensics.v1"
    enabled: set[str] = Field(default_factory=set)
    arithmetic: Arithmetic = Field(default_factory=Arithmetic)
    structure: Structure = Field(default_factory=Structure)
    extraction: Extraction = Field(default_factory=Extraction)
    duplicates: Duplicates = Field(default_factory=Duplicates)
    cross_document: CrossDocument = Field(default_factory=CrossDocument)
    verdict: Verdict = Field(default_factory=Verdict)
    next_steps: dict[str, str] = Field(default_factory=dict)  # from risk.v1.yaml

    def editor_patterns(self) -> list[re.Pattern[str]]:
        return [re.compile(p) for p in self.structure.editor_producer_patterns]


def parse_forensics(
    raw: dict[str, Any], next_steps: dict[str, str] | None = None
) -> ForensicsPolicy:
    policy = ForensicsPolicy.model_validate(raw)
    return policy.model_copy(update={"next_steps": next_steps or {}})
