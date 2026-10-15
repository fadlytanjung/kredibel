"""Scenario risk outcomes (spec 008, T008-08, AC-008-11).

AC-008-11:
- S1: every month LOW.
- S2: March CRITICAL with next step mentioning internet banking re-download.
- S4: May HIGH with next step confirming new account with the supplier using a known phone number.
"""

import json
from pathlib import Path

import pytest

from app.adapters.policy_files import load_risk_policy
from app.domain.findings import Finding
from app.domain.next_steps import next_steps_for_findings
from app.domain.risk import assess_document_risk, assess_month_risk

SYNTH_DIR = Path(__file__).resolve().parents[3] / "tools" / "synthetic" / "out"
POLICY_DIR = Path(__file__).resolve().parents[3] / "contracts" / "policy"


@pytest.fixture
def risk_policy():
    return load_risk_policy(POLICY_DIR)


def test_ac008_11_s1_every_month_low(risk_policy):
    """S1: Normal half-year has no tampering or severe findings, every month is LOW."""
    s1_truth_file = SYNTH_DIR / "S1" / "seed-1" / "truth.json"
    if not s1_truth_file.exists():
        pytest.skip(f"Synthetic scenario S1 not found at {s1_truth_file}")

    with s1_truth_file.open(encoding="utf-8") as f:
        truth = json.load(f)

    # In S1 truth, all months have clean documents and no open critical/high findings
    for month_str, _ in truth["months"].items():
        doc_assessments = []
        month_findings: list[Finding] = []

        # If scenario documents exist for month, verify they are clean
        for doc_item in truth.get("documents", []):
            if doc_item.get("month") == month_str:
                verdict = doc_item["expected"]["verdict"]
                da = assess_document_risk(verdict, [], risk_policy)
                doc_assessments.append(da)

        month_assessment = assess_month_risk(
            document_assessments=doc_assessments,
            month_findings=month_findings,
            policy=risk_policy,
        )
        assert month_assessment.level == "LOW", (
            f"Expected month {month_str} to be LOW in S1, got {month_assessment.level}"
        )


def test_ac008_11_s2_march_critical_with_next_steps(risk_policy):
    """S2: March statement edited -> March CRITICAL with next step to download original again."""
    s2_truth_file = SYNTH_DIR / "S2" / "seed-1" / "truth.json"
    if not s2_truth_file.exists():
        pytest.skip(f"Synthetic scenario S2 not found at {s2_truth_file}")

    with s2_truth_file.open(encoding="utf-8") as f:
        truth = json.load(f)

    march_expected = truth["months"]["2026-03"]
    assert march_expected["riskLevel"] == "CRITICAL"

    finding_a01 = Finding(
        finding_id="fnd_a01_running_balance",
        code="A01_RUNNING_BALANCE_BREAK",
        category="ARITHMETIC",
        severity="CRITICAL",
        title="Running balance break on 14 Mar",
        facts={},
        evidence=[],
        scope="DOCUMENT",
        doc_id="doc_acb_mar_2026",
        month="2026-03",
        status="OPEN",
    )

    doc_assessment = assess_document_risk("TAMPERED", [finding_a01], risk_policy)
    assert doc_assessment.level == "CRITICAL"

    # Month-level assessment inherits CRITICAL from document
    month_assessment = assess_month_risk(
        document_assessments=[doc_assessment],
        month_findings=[],
        policy=risk_policy,
    )
    assert month_assessment.level == "CRITICAL"

    # Check next steps catalog ordering
    steps = next_steps_for_findings([finding_a01], risk_policy)
    assert len(steps) > 0
    # Must advise downloading the statement again / asking bank for original
    step_text = steps[0].lower()
    assert (
        "download it again from internet banking" in step_text
        or "download the march statement again" in step_text
        or "original statement" in step_text
    )


def test_ac008_11_s4_may_high_with_supplier_account_change(risk_policy):
    """S4: May supplier paid to new account -> May HIGH with phone confirmation step."""
    s4_truth_file = SYNTH_DIR / "S4" / "seed-1" / "truth.json"
    if not s4_truth_file.exists():
        pytest.skip(f"Synthetic scenario S4 not found at {s4_truth_file}")

    with s4_truth_file.open(encoding="utf-8") as f:
        truth = json.load(f)

    may_expected = truth["months"]["2026-05"]
    assert may_expected["riskLevel"] == "HIGH"
    assert "X08_SUPPLIER_ACCOUNT_CHANGED" in may_expected["monthFindings"]

    finding_x08 = Finding(
        finding_id="fnd_x08_supplier_account",
        code="X08_SUPPLIER_ACCOUNT_CHANGED",
        category="CROSS_DOCUMENT",
        severity="HIGH",
        title="Roastline Equipment Service paid to a new account",
        facts={},
        evidence=[],
        scope="MONTH",
        month="2026-05",
        status="OPEN",
    )

    doc_clean = assess_document_risk("CLEAN", [], risk_policy)
    month_assessment = assess_month_risk(
        document_assessments=[doc_clean],
        month_findings=[finding_x08],
        policy=risk_policy,
    )
    assert month_assessment.level == "HIGH"

    # Next steps for X08
    steps = next_steps_for_findings([finding_x08], risk_policy)
    assert len(steps) > 0
    assert "phone number you already have" in steps[0].lower()
