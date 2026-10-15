"""Findings: the shape every check produces (docs/08 §1), and how a re-run updates them. Pure."""

from dataclasses import dataclass, field, replace
from typing import Any, Literal

from app.core.ids import content_id

Severity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
Category = Literal[
    "SCREENING",
    "EXTRACTION",
    "DUPLICATE",
    "ARITHMETIC",
    "STRUCTURE",
    "VISUAL",
    "CROSS_DOCUMENT",
    "RECONCILIATION",
    "BEHAVIOURAL",
]
FindingStatus = Literal["OPEN", "ACKNOWLEDGED", "DISMISSED", "RESOLVED"]
SEVERITY_RANK: dict[str, int] = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


@dataclass(frozen=True)
class Evidence:
    doc_id: str | None = None
    page: int | None = None
    bbox: dict[str, float] | None = None  # normalized 0..1, top-left origin
    tx_id: str | None = None
    invoice_id: str | None = None
    receipt_id: str | None = None
    ledger_entry_id: str | None = None
    label: str | None = None


@dataclass
class Finding:
    finding_id: str
    code: str
    category: Category
    severity: Severity
    title: str
    facts: dict[str, str]
    evidence: list[Evidence]
    scope: Literal["DOCUMENT", "MONTH"] = "DOCUMENT"
    doc_id: str | None = None
    month: str | None = None
    next_steps: list[str] = field(default_factory=list)
    explanation: str | None = None
    detected_by: Literal["RULE", "MODEL", "MODEL_ARMOR"] = "RULE"
    status: FindingStatus = "OPEN"
    dismissal: dict[str, Any] | None = None
    last_seen_run_id: str | None = None

    @property
    def severity_rank(self) -> int:
        return SEVERITY_RANK[self.severity]


def finding_id(code: str, anchor: str) -> str:
    """Stable across re-runs: the same problem at the same place keeps its ID (docs/08 §1)."""
    return content_id("fnd", code, anchor)


def merge_findings(existing: list[Finding], fresh: list[Finding]) -> list[Finding]:
    """A re-run's findings upserted over the stored ones: what no longer applies is RESOLVED,
    ACKNOWLEDGED and DISMISSED keep their status and dismissal (docs/08 §1)."""
    before = {f.finding_id: f for f in existing}
    out: list[Finding] = []
    for f in fresh:
        old = before.pop(f.finding_id, None)
        if old is not None and old.status in ("ACKNOWLEDGED", "DISMISSED"):
            f = replace(f, status=old.status, dismissal=old.dismissal)
        out.append(f)
    for old in before.values():
        out.append(
            old if old.status in ("DISMISSED", "RESOLVED") else replace(old, status="RESOLVED")
        )
    return sorted(out, key=lambda f: (f.severity_rank, f.code, f.finding_id))
