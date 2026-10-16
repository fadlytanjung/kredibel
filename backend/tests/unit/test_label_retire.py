"""A value label stops asking once the readings agree (spec 016): retired unless a person decided
it. Synthetic data only."""

from dataclasses import replace
from datetime import UTC, datetime

from app.agents.labels import decision
from app.domain.label_sync import retired_value_labels
from app.domain.labels import LabelSubject, LearningPolicy, decide, propose

AT = datetime(2026, 10, 16, tzinfo=UTC)
POLICY = LearningPolicy(needs_check_below={})


def _value(tx: str, field: str):
    return propose(
        "FIELD_VALUE",
        LabelSubject(display=f"{tx} · {field}", doc_id="doc_1", page_no=1, field=field, tx_id=tx),
        decision("1,000.00", source="MODEL", at=AT),
        policy=POLICY,
    )


def test_a_value_label_retires_when_the_readings_now_agree_unless_a_person_decided_it():
    still_open = _value("tx_1", "amount")
    now_agreed = _value("tx_2", "amount")
    decided = decide(_value("tx_3", "balance"), action="CONFIRM", by="u-1", at=AT, policy=POLICY)
    other_task = replace(_value("tx_4", "date"), task="CATEGORY")

    retired = retired_value_labels([still_open, now_agreed, decided, other_task], [still_open])

    assert retired == [now_agreed.label_id]
