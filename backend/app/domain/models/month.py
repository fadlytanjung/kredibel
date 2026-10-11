"""Domain model for Month and MonthState (docs/09 §3.9).

Normative references: docs/09 §3.9, docs/06 §3, contracts/openapi.yaml.
Pure domain logic: no framework dependencies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class MonthState(StrEnum):
    COLLECTING = "COLLECTING"
    RECONCILING = "RECONCILING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    RECONCILED = "RECONCILED"
    SIGNED_OFF = "SIGNED_OFF"


@dataclass
class Month:
    month: str  # yyyy-mm format
    state: MonthState = MonthState.COLLECTING
    dirty: bool = False
    generation: int = 0
    statements: list[dict[str, Any]] = field(default_factory=list)
    figures: dict[str, Any] = field(default_factory=dict)
    risk: dict[str, Any] = field(default_factory=dict)
    flows: dict[str, Any] = field(default_factory=dict)
    note: str | None = None
    last_run_id: str | None = None
    updated_at: datetime | None = None
