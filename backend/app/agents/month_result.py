"""Run-local computation, kept out of ADK events and persisted only after the generation check."""

from dataclasses import dataclass, field
from typing import Any

from app.agents.month_data import MonthData
from app.domain.findings import Finding
from app.domain.models.match import StoredMatch
from app.domain.reconcile import Allocation


@dataclass
class MonthResult:
    data: MonthData
    allocations: list[Allocation]
    matches: list[StoredMatch]
    support: dict[str, tuple[str, list[str], str]] = field(default_factory=dict)
    invoice_evidence: dict[str, dict[str, Any]] = field(default_factory=dict)
    receipt_evidence: dict[str, dict[str, Any]] = field(default_factory=dict)
    findings: list[Finding] | None = None


PendingMonths = dict[tuple[str, str], MonthResult]


def run_key(node_input: dict[str, Any]) -> tuple[str, str]:
    return str(node_input.get("orgId") or ""), str(node_input.get("runId") or "")
