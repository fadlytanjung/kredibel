"""Unit tests for fraud risk levels, score, and reasons (spec 008, T008-01, AC-008-1..3)."""

from pathlib import Path

import pytest

from app.adapters.policy_files import load_risk_policy
from app.domain.findings import Finding
from app.domain.risk import (
    RiskAssessment,
    assess_document_risk,
    assess_month_risk,
    calculate_risk_score,
)

POLICY_DIR = Path(__file__).resolve().parents[3] / "contracts" / "policy"


@pytest.fixture
def policy():
    return load_risk_policy(POLICY_DIR)


def make_finding(
    fid: str,
    code: str,
    severity: str = "LOW",
    status: str = "OPEN",
    category: str = "ARITHMETIC",
) -> Finding:
    return Finding(
        finding_id=fid,
        code=code,
        category=category,  # type: ignore
        severity=severity,  # type: ignore
        title=f"Finding {code}",
        facts={},
        evidence=[],
        status=status,  # type: ignore
    )


class TestDocumentRisk:
    """AC-008-1, AC-008-3: Document level from findings and verdict."""

    def test_clean_document_without_findings_is_low(self, policy):
        assessment = assess_document_risk("CLEAN", [], policy)
        assert assessment.level == "LOW"
        assert assessment.score == 0
        assert assessment.reasons == ()

    def test_tampered_verdict_makes_document_critical(self, policy):
        assessment = assess_document_risk("TAMPERED", [], policy)
        assert assessment.level == "CRITICAL"

    def test_s01_finding_makes_document_critical(self, policy):
        f = make_finding("f1", "S01_EMBEDDED_INSTRUCTIONS", severity="CRITICAL")
        assessment = assess_document_risk("CLEAN", [f], policy)
        assert assessment.level == "CRITICAL"
        assert "f1" in assessment.reasons

    def test_suspicious_verdict_or_high_finding_makes_document_high(self, policy):
        assessment = assess_document_risk("SUSPICIOUS", [], policy)
        assert assessment.level == "HIGH"

        f = make_finding("f2", "A01_RUNNING_BALANCE_BREAK", severity="HIGH")
        assessment = assess_document_risk("CLEAN", [f], policy)
        assert assessment.level == "HIGH"
        assert assessment.reasons == ("f2",)

    def test_unverifiable_or_medium_finding_makes_document_medium(self, policy):
        assessment = assess_document_risk("UNVERIFIABLE", [], policy)
        assert assessment.level == "MEDIUM"

        f = make_finding("f3", "E01_EXTRACTION_FAILURE", severity="MEDIUM")
        assessment = assess_document_risk("CLEAN", [f], policy)
        assert assessment.level == "MEDIUM"
        assert assessment.reasons == ("f3",)

    def test_dismissed_finding_does_not_raise_level_or_score(self, policy):
        # AC-008-3: dismissed findings do not raise level; acknowledged ones still do.
        dismissed = make_finding(
            "f4", "A01_RUNNING_BALANCE_BREAK", severity="HIGH", status="DISMISSED"
        )
        assessment = assess_document_risk("CLEAN", [dismissed], policy)
        assert assessment.level == "LOW"
        assert assessment.score == 0
        assert assessment.reasons == ()

    def test_acknowledged_finding_still_raises_level_and_score(self, policy):
        # AC-008-3: acknowledged findings still raise level.
        ack = make_finding(
            "f5", "A01_RUNNING_BALANCE_BREAK", severity="HIGH", status="ACKNOWLEDGED"
        )
        assessment = assess_document_risk("CLEAN", [ack], policy)
        assert assessment.level == "HIGH"
        assert assessment.score == 20
        assert assessment.reasons == ("f5",)


class TestRiskScore:
    """AC-008-2: Risk score calculation with weights and max 100."""

    def test_score_weights_and_cap(self, policy):
        findings = [
            make_finding("f1", "CRIT_1", severity="CRITICAL"),  # 40
            make_finding("f2", "CRIT_2", severity="CRITICAL"),  # 40
            make_finding("f3", "HIGH_1", severity="HIGH"),  # 20 -> sum 100
            make_finding("f4", "MED_1", severity="MEDIUM"),  # 8  -> sum 108 -> capped at 100
        ]
        score = calculate_risk_score(findings, policy)
        assert score == 100

    def test_score_ignores_dismissed_and_resolved(self, policy):
        findings = [
            make_finding("f1", "HIGH_1", severity="HIGH", status="OPEN"),
            make_finding("f2", "HIGH_2", severity="HIGH", status="DISMISSED"),
            make_finding("f3", "HIGH_3", severity="HIGH", status="RESOLVED"),
        ]
        score = calculate_risk_score(findings, policy)
        assert score == 20


class TestMonthRisk:
    """AC-008-1: Month level inheritance and specific month rules."""

    def test_month_inherits_critical_from_tampered_document(self, policy):
        doc_assessment = RiskAssessment(level="CRITICAL", score=40, reasons=("f_doc_1",))
        month_assessment = assess_month_risk([doc_assessment], [], policy)
        assert month_assessment.level == "CRITICAL"
        assert "f_doc_1" in month_assessment.reasons

    def test_month_rule_x08_makes_month_high(self, policy):
        f = make_finding("f_x08", "X08_SUPPLIER_ACCOUNT_CHANGED", severity="MEDIUM", status="OPEN")
        month_assessment = assess_month_risk([], [f], policy)
        assert month_assessment.level == "HIGH"
        assert "f_x08" in month_assessment.reasons

    def test_month_rule_d07_makes_month_high(self, policy):
        f = make_finding("f_d07", "D07_DOUBLE_PAYMENT", severity="MEDIUM", status="OPEN")
        month_assessment = assess_month_risk([], [f], policy)
        assert month_assessment.level == "HIGH"
        assert "f_d07" in month_assessment.reasons

    def test_month_rule_x09_makes_month_high(self, policy):
        f = make_finding("f_x09", "X09_LEDGER_BANK_MISMATCH", severity="HIGH", status="OPEN")
        month_assessment = assess_month_risk([], [f], policy)
        assert month_assessment.level == "HIGH"
        assert "f_x09" in month_assessment.reasons

    def test_dismissed_month_rule_does_not_raise_level(self, policy):
        f = make_finding(
            "f_x08", "X08_SUPPLIER_ACCOUNT_CHANGED", severity="MEDIUM", status="DISMISSED"
        )
        month_assessment = assess_month_risk([], [f], policy)
        assert month_assessment.level == "LOW"
        assert month_assessment.reasons == ()


class TestNextSteps:
    """AC-008-4: Deterministic next steps catalog lookup."""

    def test_catalog_lookup_and_ordering(self, policy):
        from app.domain.next_steps import next_steps_for_findings

        findings = [
            make_finding("f1", "R01_SALES_INVOICE_OVERDUE", severity="LOW"),
            make_finding("f2", "A01_RUNNING_BALANCE_BREAK", severity="CRITICAL"),
            make_finding("f3", "X08_SUPPLIER_ACCOUNT_CHANGED", severity="HIGH"),
        ]
        steps = next_steps_for_findings(findings, policy)
        # CRITICAL (A01) comes first, then HIGH (X08), then LOW (R01)
        assert len(steps) == 3
        assert "Ask the bank for the original statement" in steps[0]
        assert "Confirm the new account with the supplier" in steps[1]
        assert "Send a reminder to the client" in steps[2]

    def test_catalog_lookup_ignores_dismissed(self, policy):
        from app.domain.next_steps import next_steps_for_findings

        findings = [
            make_finding(
                "f1", "A01_RUNNING_BALANCE_BREAK", severity="CRITICAL", status="DISMISSED"
            ),
            make_finding("f2", "X08_SUPPLIER_ACCOUNT_CHANGED", severity="HIGH", status="OPEN"),
        ]
        steps = next_steps_for_findings(findings, policy)
        assert len(steps) == 1
        assert "Confirm the new account with the supplier" in steps[0]
