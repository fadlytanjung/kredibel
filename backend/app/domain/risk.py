"""Fraud risk levels per document and month (spec 008, AC-008-1..3; docs/08 §8). Pure."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.domain.findings import Finding

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

LEVEL_RANK: dict[RiskLevel, int] = {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
    "CRITICAL": 3,
}

RANK_TO_LEVEL: dict[int, RiskLevel] = {v: k for k, v in LEVEL_RANK.items()}


@dataclass(frozen=True)
class RiskAssessment:
    level: RiskLevel
    score: int  # 0..100
    reasons: tuple[str, ...] = ()  # finding IDs behind the level


class RiskDocumentPolicy(BaseModel):
    model_config = ConfigDict(extra="ignore")
    critical_verdicts: list[str] = ["TAMPERED"]
    critical_codes: list[str] = ["S01_EMBEDDED_INSTRUCTIONS"]
    high_verdicts: list[str] = ["SUSPICIOUS"]
    high_severities: list[str] = ["HIGH"]
    medium_verdicts: list[str] = ["UNVERIFIABLE"]
    medium_severities: list[str] = ["MEDIUM"]


class MonthRule(BaseModel):
    model_config = ConfigDict(extra="ignore")
    code: str
    level: RiskLevel = "HIGH"
    severity: str | None = None


class RiskMonthPolicy(BaseModel):
    model_config = ConfigDict(extra="ignore")
    inherit_from_documents: bool = True
    rules: list[MonthRule] = field(default_factory=list)


class RiskScorePolicy(BaseModel):
    model_config = ConfigDict(extra="ignore")
    weights: dict[str, int] = {
        "CRITICAL": 40,
        "HIGH": 20,
        "MEDIUM": 8,
        "LOW": 2,
        "INFO": 0,
    }
    max: int = 100


class RiskPolicy(BaseModel):
    model_config = ConfigDict(extra="ignore")
    version: int = 1
    id: str = "risk.v1"
    levels: list[RiskLevel] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    document: RiskDocumentPolicy = field(default_factory=RiskDocumentPolicy)
    month: RiskMonthPolicy = field(default_factory=RiskMonthPolicy)
    score: RiskScorePolicy = field(default_factory=RiskScorePolicy)
    next_steps: dict[str, str] = field(default_factory=dict)


def parse_risk_policy(raw: dict[str, Any]) -> RiskPolicy:
    """Parse raw risk.v1.yaml dictionary into pure RiskPolicy."""
    doc_raw = raw.get("document", {})
    crit = doc_raw.get("CRITICAL", {})
    high = doc_raw.get("HIGH", {})
    med = doc_raw.get("MEDIUM", {})

    doc_policy = RiskDocumentPolicy(
        critical_verdicts=crit.get("verdicts", ["TAMPERED"]),
        critical_codes=crit.get("openCodes", ["S01_EMBEDDED_INSTRUCTIONS"]),
        high_verdicts=high.get("verdicts", ["SUSPICIOUS"]),
        high_severities=high.get("openSeverities", ["HIGH"]),
        medium_verdicts=med.get("verdicts", ["UNVERIFIABLE"]),
        medium_severities=med.get("openSeverities", ["MEDIUM"]),
    )

    month_raw = raw.get("month", {})
    month_rules = [
        MonthRule(
            code=r.get("code", ""),
            level=r.get("level", "HIGH"),
            severity=r.get("severity"),
        )
        for r in month_raw.get("rules", [])
    ]
    month_policy = RiskMonthPolicy(
        inherit_from_documents=month_raw.get("inheritFromDocuments", True),
        rules=month_rules,
    )

    score_raw = raw.get("score", {})
    default_weights = {"CRITICAL": 40, "HIGH": 20, "MEDIUM": 8, "LOW": 2, "INFO": 0}
    score_policy = RiskScorePolicy(
        weights=score_raw.get("weights", default_weights),
        max=score_raw.get("max", 100),
    )

    return RiskPolicy(
        version=raw.get("version", 1),
        id=raw.get("id", "risk.v1"),
        levels=raw.get("levels", ["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
        document=doc_policy,
        month=month_policy,
        score=score_policy,
        next_steps=raw.get("nextSteps", {}),
    )


def calculate_risk_score(findings: Sequence[Finding], policy: RiskPolicy) -> int:
    """Risk score 0–100 calculated over live (OPEN / ACKNOWLEDGED) findings (AC-008-2, AC-008-3)."""
    live = [f for f in findings if f.status in ("OPEN", "ACKNOWLEDGED")]
    raw = sum(policy.score.weights.get(f.severity, 0) for f in live)
    return min(policy.score.max, raw)


def assess_document_risk(
    verdict: str | None,
    findings: Sequence[Finding],
    policy: RiskPolicy,
) -> RiskAssessment:
    """Document level and score from its findings and verdict (AC-008-1..3; docs/08 §8).

    - CRITICAL if verdict is TAMPERED or an open S01.
    - HIGH if verdict is SUSPICIOUS or open HIGH finding.
    - MEDIUM if verdict is UNVERIFIABLE or open MEDIUM finding.
    - otherwise LOW.
    Dismissed findings do not count; acknowledged ones still do.
    """
    live = [f for f in findings if f.status in ("OPEN", "ACKNOWLEDGED")]
    score = calculate_risk_score(findings, policy)

    # Check CRITICAL
    critical_reasons: list[str] = [
        f.finding_id for f in live if f.code.startswith("S01") or f.severity == "CRITICAL"
    ]
    if verdict in policy.document.critical_verdicts or critical_reasons:
        return RiskAssessment(
            level="CRITICAL",
            score=score,
            reasons=tuple(critical_reasons),
        )

    # Check HIGH
    high_reasons: list[str] = [f.finding_id for f in live if f.severity == "HIGH"]
    if verdict in policy.document.high_verdicts or high_reasons:
        return RiskAssessment(
            level="HIGH",
            score=score,
            reasons=tuple(high_reasons),
        )

    # Check MEDIUM
    medium_reasons: list[str] = [f.finding_id for f in live if f.severity == "MEDIUM"]
    if verdict in policy.document.medium_verdicts or medium_reasons:
        return RiskAssessment(
            level="MEDIUM",
            score=score,
            reasons=tuple(medium_reasons),
        )

    low_reasons: list[str] = [f.finding_id for f in live if f.severity == "LOW"]
    return RiskAssessment(
        level="LOW",
        score=score,
        reasons=tuple(low_reasons),
    )


def assess_month_risk(
    document_assessments: Sequence[RiskAssessment],
    month_findings: Sequence[Finding],
    policy: RiskPolicy,
) -> RiskAssessment:
    """Month level: highest of document levels, month findings, and month rules (AC-008-1)."""
    live_month = [f for f in month_findings if f.status in ("OPEN", "ACKNOWLEDGED")]

    max_rank = LEVEL_RANK["LOW"]
    reasons: list[str] = []

    # 1. Inherit from documents if enabled
    if policy.month.inherit_from_documents and document_assessments:
        for da in document_assessments:
            da_rank = LEVEL_RANK[da.level]
            if da_rank > max_rank:
                max_rank = da_rank
                reasons = list(da.reasons)
            elif da_rank == max_rank and da_rank > 0:
                reasons.extend(da.reasons)

    # 2. Check month findings by severity
    for f in live_month:
        f_rank = LEVEL_RANK.get(f.severity if f.severity in LEVEL_RANK else "LOW", 0)  # type: ignore
        if f_rank > max_rank:
            max_rank = f_rank
            reasons = [f.finding_id]
        elif f_rank == max_rank and f_rank > 0:
            if f.finding_id not in reasons:
                reasons.append(f.finding_id)

    # 3. Check specific month rules (X08, D07, X09)
    for rule in policy.month.rules:
        matching = [
            f
            for f in live_month
            if (f.code == rule.code or f.code.startswith(rule.code.split("_")[0]))
            and (rule.severity is None or f.severity == rule.severity)
        ]
        if matching:
            rule_rank = LEVEL_RANK[rule.level]
            if rule_rank > max_rank:
                max_rank = rule_rank
                reasons = [f.finding_id for f in matching]
            elif rule_rank == max_rank and rule_rank > 0:
                for f in matching:
                    if f.finding_id not in reasons:
                        reasons.append(f.finding_id)

    # Deduplicate reasons maintaining order
    seen: set[str] = set()
    deduped_reasons: list[str] = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            deduped_reasons.append(r)

    # Total score includes document scores and month findings
    doc_scores = sum(da.score for da in document_assessments)
    month_score = calculate_risk_score(month_findings, policy)
    total_score = min(policy.score.max, doc_scores + month_score)

    return RiskAssessment(
        level=RANK_TO_LEVEL[max_rank],
        score=total_score,
        reasons=tuple(deduped_reasons),
    )
