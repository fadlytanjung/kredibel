"""Labels (spec 016, T016-01): deterministic IDs, people win over re-runs, needsCheck from the
policy, decisions and the dataset split. Synthetic subjects only."""

from datetime import UTC, datetime
from decimal import Decimal as D
from pathlib import Path

from app.adapters.policy_files import load_learning_policy
from app.domain.labels import (
    AiDecision,
    LabelSubject,
    dataset_split,
    decide,
    label_id,
    merge,
    needs_check,
    propose,
    rule_for,
    summarize,
)

POLICY = load_learning_policy(Path(__file__).resolve().parents[3] / "contracts/policy")
AT = datetime(2026, 7, 2, 9, 14, tzinfo=UTC)
LINE = LabelSubject(
    display="TRANSFER OUT ROASTLINE EQUIPMENT", doc_id="doc_may", page_no=1, tx_id="tx_1"
)


def ai(value: str, confidence: str | None = "0.66", run: str = "run_1") -> AiDecision:
    return AiDecision(
        value=value,
        source="MODEL",
        at=AT,
        confidence=D(confidence) if confidence else None,
        model="gemini-flash-lite",
        prompt_version="categorize v4",
        run_id=run,
    )


def test_ac016_2_the_id_is_the_task_and_the_subject_so_a_re_run_upserts():
    assert label_id("CATEGORY", LINE) == label_id("CATEGORY", LINE)
    assert label_id("CATEGORY", LINE) != label_id("FIELD_VALUE", LINE)
    assert label_id("CATEGORY", LINE).startswith("lbl_") and len(label_id("CATEGORY", LINE)) == 20
    other = LabelSubject(display="other words", doc_id="doc_may", page_no=1, tx_id="tx_1")
    assert label_id("CATEGORY", other) == label_id("CATEGORY", LINE), "the display is not identity"


def test_ac016_3_needs_check_follows_the_policy_per_task():
    assert needs_check("CATEGORY", D("0.66"), POLICY) is True
    assert needs_check("CATEGORY", D("0.70"), POLICY) is False
    assert needs_check("DOC_TYPE", D("0.79"), POLICY) is True
    assert needs_check("FIELD_VALUE", D("1.0"), POLICY) is True, "every disagreed value asks"
    assert needs_check("CATEGORY", None, POLICY) is True


def test_ac016_2_people_win_over_every_later_run():
    first = propose("CATEGORY", LINE, ai("SUPPLIER_PAYMENT"), policy=POLICY, month="2026-05")
    assert (
        first.status == "AI_PROPOSED"
        and first.needs_check
        and first.final_value == "SUPPLIER_PAYMENT"
    )
    assert first.dataset_use == "EXCLUDED"
    corrected = decide(
        first,
        action="CORRECT",
        by="u-1",
        at=AT,
        policy=POLICY,
        value="INVENTORY_PURCHASE",
        note="goods",
    )
    assert corrected.status == "CORRECTED" and corrected.final_value == "INVENTORY_PURCHASE"
    assert (
        corrected.final_source == "PERSON"
        and corrected.decided_by == "u-1"
        and not corrected.needs_check
    )
    assert corrected.dataset_use in ("TRAIN", "EVAL")
    for run in range(1, 6):
        again = propose(
            "CATEGORY",
            LINE,
            ai("SUPPLIER_PAYMENT", "0.9", f"run_{run}"),
            policy=POLICY,
            month="2026-05",
        )
        stored = merge(corrected, again)
        assert stored.status == "CORRECTED" and stored.final_value == "INVENTORY_PURCHASE"
        assert stored.ai.run_id == f"run_{run}" and stored.ai.confidence == D("0.9")
        assert stored.ai_disagrees_with_person is True and stored.needs_check is False
        assert stored.decided_by == "u-1" and stored.note == "goods"
    agreeing = merge(
        corrected, propose("CATEGORY", LINE, ai("INVENTORY_PURCHASE", "0.95"), policy=POLICY)
    )
    assert agreeing.ai_disagrees_with_person is False
    # An undecided label simply takes the new decision.
    fresh = merge(first, propose("CATEGORY", LINE, ai("RENT", "0.92"), policy=POLICY))
    assert fresh.final_value == "RENT" and fresh.needs_check is False


def test_ac016_6_confirm_verifies_and_the_split_is_fixed_by_the_id():
    label = propose(
        "DOC_TYPE",
        LabelSubject(display="RES-0045.pdf", doc_id="doc_res"),
        ai("PURCHASE_INVOICE", "0.97"),
        policy=POLICY,
    )
    verified = decide(label, action="CONFIRM", by="u-1", at=AT, policy=POLICY)
    assert verified.status == "VERIFIED" and verified.final_value == "PURCHASE_INVOICE"
    assert verified.dataset_use == dataset_split(label.label_id, POLICY.eval_share)
    assert dataset_split(label.label_id, POLICY.eval_share) == dataset_split(
        label.label_id, POLICY.eval_share
    )
    ids = [label_id("CATEGORY", LabelSubject(display="x", tx_id=f"tx_{i}")) for i in range(400)]
    share = sum(1 for i in ids if dataset_split(i, POLICY.eval_share) == "EVAL") / len(ids)
    assert 0.12 < share < 0.28, share
    try:
        decide(label, action="CORRECT", by="u-1", at=AT, policy=POLICY, value="  ")
    except ValueError:
        pass
    else:
        raise AssertionError("a correction without a value")


def test_ac016_5_the_summary_counts_what_people_checked_and_how_often_the_ai_was_right():
    a = propose("CATEGORY", LINE, ai("SUPPLIER_PAYMENT"), policy=POLICY)
    b = decide(
        propose(
            "CATEGORY", LabelSubject(display="b", tx_id="tx_2"), ai("RENT", "0.9"), policy=POLICY
        ),
        action="CONFIRM",
        by="u",
        at=AT,
        policy=POLICY,
    )
    c = decide(
        propose(
            "CATEGORY", LabelSubject(display="c", tx_id="tx_3"), ai("RENT", "0.9"), policy=POLICY
        ),
        action="CORRECT",
        by="u",
        at=AT,
        policy=POLICY,
        value="UTILITIES",
    )
    summary = summarize([a, b, c])
    assert {
        k: summary[k]
        for k in ("total", "needsCheck", "verified", "corrected", "aiAgreementOnChecked")
    } == {
        "total": 3,
        "needsCheck": 1,
        "verified": 1,
        "corrected": 1,
        "aiAgreementOnChecked": 0.5,
    }
    assert summary["byTask"]["CATEGORY"] == 3
    assert summary["byStatus"] == {"AI_PROPOSED": 1, "VERIFIED": 1, "CORRECTED": 1}
    assert summarize([a])["aiAgreementOnChecked"] is None


def test_ac016_7_a_correction_remembered_for_the_party_and_direction():
    label = decide(
        propose("CATEGORY", LINE, ai("SUPPLIER_PAYMENT"), policy=POLICY),
        action="CORRECT",
        by="u-1",
        at=AT,
        policy=POLICY,
        value="INVENTORY_PURCHASE",
    )
    rule = rule_for(label, counterparty_key="cp_roastline", direction="out", by="u-1", at=AT)
    assert (
        rule.category == "INVENTORY_PURCHASE"
        and rule.direction == "out"
        and rule.source_label_id == label.label_id
    )
    assert (
        rule.rule_id
        == rule_for(
            label, counterparty_key="cp_roastline", direction="out", by="u-2", at=AT
        ).rule_id
    )
