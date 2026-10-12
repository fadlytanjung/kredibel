"""A document's integrity verdict from its own findings (docs/08 §3). Pure."""

from typing import Literal

from app.domain.checks.policy import ForensicsPolicy
from app.domain.findings import Finding

Verdict = Literal["CLEAN", "SUSPICIOUS", "TAMPERED", "UNVERIFIABLE"]


def integrity_verdict(findings: list[Finding], policy: ForensicsPolicy) -> Verdict:
    """Top-down: TAMPERED, SUSPICIOUS, UNVERIFIABLE, CLEAN. Extraction findings speak to how well
    the page was read, not to tampering: they make a document UNVERIFIABLE, never SUSPICIOUS."""
    live = [
        f
        for f in findings
        if f.status in ("OPEN", "ACKNOWLEDGED")
        and f.category in policy.verdict.integrity_categories
    ]
    if any(f.code in policy.verdict.tampered_codes and f.severity == "CRITICAL" for f in live):
        return "TAMPERED"
    tamper_signals = [f for f in live if f.category != "EXTRACTION"]
    mediums = sum(1 for f in tamper_signals if f.severity == "MEDIUM")
    if (
        any(f.code.startswith("S01") for f in live)
        or any(f.severity in ("CRITICAL", "HIGH") for f in tamper_signals)
        or mediums >= policy.verdict.suspicious_medium_count
    ):
        return "SUSPICIOUS"
    if any(f.code.startswith(("E01", "E02")) for f in live):
        return "UNVERIFIABLE"
    return "CLEAN"
