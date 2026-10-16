"""E-LBL measurements (spec 016, T016-09, AC-016-10; docs/15 §5): AI agreement with person-checked
labels per task, calibration per confidence bucket of learning.v1.yaml, disagreements after
re-runs and person labels overwritten. Synthetic labels only."""

from datetime import UTC, datetime
from decimal import Decimal as D
from pathlib import Path

from app.adapters.policy_files import load_learning_policy
from app.domain.label_metrics import label_report
from app.domain.labels import AiDecision, LabelSubject, decide, merge, propose

POLICY = load_learning_policy(Path(__file__).resolve().parents[3] / "contracts/policy")
AT = datetime(2026, 7, 2, tzinfo=UTC)


def checked(i: int, task: str, ai: str, confidence: str | None, person: str):
    label = propose(
        task,  # type: ignore[arg-type]
        LabelSubject(display=f"s{i}", tx_id=f"tx_{i}"),
        AiDecision(
            value=ai, source="MODEL", at=AT, confidence=D(confidence) if confidence else None
        ),
        policy=POLICY,
    )
    action = "CONFIRM" if person == ai else "CORRECT"
    return decide(label, action=action, by="truth", at=AT, policy=POLICY, value=person)


def test_ac016_10_agreement_per_task_and_calibration_per_bucket():
    labels = [
        checked(1, "CATEGORY", "RENT", "0.95", "RENT"),
        checked(2, "CATEGORY", "RENT", "0.92", "UTILITIES"),
        checked(3, "CATEGORY", "PAYROLL", "0.65", "PAYROLL"),
        checked(4, "DOC_TYPE", "RECEIPT", "0.99", "RECEIPT"),
        checked(5, "DOC_TYPE", "RECEIPT", None, "RECEIPT"),
        propose(  # never checked by a person: not measured
            "CATEGORY",
            LabelSubject(display="s6", tx_id="tx_6"),
            AiDecision(value="RENT", source="MODEL", at=AT, confidence=D("0.99")),
            policy=POLICY,
        ),
    ]
    report = label_report(labels, POLICY.calibration_buckets)
    assert report["tasks"]["CATEGORY"] == {"checked": 3, "agreed": 2, "agreement": 0.6667}
    assert report["tasks"]["DOC_TYPE"] == {"checked": 2, "agreed": 2, "agreement": 1.0}
    assert "PAGE_TYPE" not in report["tasks"]
    buckets = {b["upTo"]: b for b in report["calibration"]}
    assert buckets["0.7"] == {
        "from": "0.5",
        "upTo": "0.7",
        "labels": 1,
        "meanConfidence": 0.65,
        "accuracy": 1.0,
        "gap": 0.35,
    }
    assert buckets["0.95"]["labels"] == 2 and buckets["0.95"]["accuracy"] == 0.5
    assert buckets["1.0"]["labels"] == 1 and buckets["1.0"]["gap"] == 0.01
    assert report["unscored"] == 1  # checked, but the AI gave no confidence
    assert report["worstGap"] == 0.435
    assert report["personLabelsOverwritten"] == 0 and report["disagreementsAfterRerun"] == 0


def test_ac016_10_a_later_run_that_disagrees_is_counted_and_nothing_is_overwritten():
    label = checked(1, "CATEGORY", "RENT", "0.80", "UTILITIES")
    rerun = merge(
        label,
        propose(
            "CATEGORY",
            LabelSubject(display="s1", tx_id="tx_1"),
            AiDecision(value="RENT", source="MODEL", at=AT, confidence=D("0.9")),
            policy=POLICY,
        ),
    )
    report = label_report([rerun], POLICY.calibration_buckets)
    assert report["disagreementsAfterRerun"] == 1 and report["personLabelsOverwritten"] == 0
