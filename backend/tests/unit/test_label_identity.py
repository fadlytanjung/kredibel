"""A label about a bank line is that line's label, whatever counterparty the line has today (spec
016): the line's counterparty can be assigned after its category, and it must not fork the label.
Synthetic data only."""

from dataclasses import replace
from datetime import UTC, datetime

from app.agents.labels import decision
from app.domain.labels import LabelSubject, LearningPolicy, decide, label_id, propose, relabel_plan

AT = datetime(2026, 10, 16, tzinfo=UTC)
POLICY = LearningPolicy(needs_check_below={})


def _category(cp: str | None, at: datetime = AT):
    subject = LabelSubject(
        display="tx_1", doc_id="doc_1", page_no=1, tx_id="tx_1", counterparty_id=cp
    )
    return propose("CATEGORY", subject, decision("BANK_FEES", source="MODEL", at=at), policy=POLICY)


def test_a_lines_label_id_ignores_the_counterparty_a_counterpartys_does_not():
    line = LabelSubject(display="x", doc_id="doc_1", tx_id="tx_1")
    assert label_id("CATEGORY", line) == label_id("CATEGORY", replace(line, counterparty_id="cp_1"))
    party = LabelSubject(display="x", counterparty_id="cp_1")
    assert label_id("COUNTERPARTY_ROLE", party) != label_id(
        "COUNTERPARTY_ROLE", replace(party, counterparty_id="cp_2")
    )


def test_a_lines_forked_labels_fold_into_one_keeping_a_persons_decision():
    canonical = label_id(
        "CATEGORY", LabelSubject(display="", doc_id="doc_1", page_no=1, tx_id="tx_1")
    )
    # Stored under the old identity (with the counterparty in the ID).
    model_early = replace(_category(None), label_id="lbl_old_a")
    person = replace(
        decide(_category("cp_1"), action="CONFIRM", by="u-1", at=AT, policy=POLICY),
        label_id="lbl_old_b",
    )
    model_late = replace(_category("cp_2", AT.replace(hour=5)), label_id="lbl_old_c")

    plan = relabel_plan([model_early, person, model_late])

    assert plan.rekey == [("lbl_old_b", canonical)]
    assert sorted(plan.delete) == ["lbl_old_a", "lbl_old_c"]


def test_labels_already_under_their_identity_are_left_alone():
    assert relabel_plan([_category("cp_1")]).rekey == []
    assert relabel_plan([_category("cp_1")]).delete == []
