"""An answer with a table or chart is stored in Firestore (spec 011): Firestore holds no list in a
list, so each row is kept as {"cells": [...]} and read back as the row it was. Synthetic data."""

from datetime import UTC, datetime
from typing import Any

from app.adapters.firestore.assistant_repo import _msg_to_doc, _msg_to_domain
from app.domain.models.assistant import AnswerPart, AssistantMessage, MessageAnswer


def _nested_lists(value: Any, inside_list: bool = False) -> bool:
    if isinstance(value, list):
        return inside_list or any(_nested_lists(v, True) for v in value)
    if isinstance(value, dict):
        return any(_nested_lists(v) for v in value.values())
    return False


def test_an_answer_with_rows_is_stored_without_a_list_in_a_list_and_reads_back():
    answer = MessageAnswer(
        parts=[
            AnswerPart(type="text", text="Money out in October 2026 was IDR 152,306,418.00."),
            AnswerPart(
                type="chart",
                chart="MONTHLY_IN_OUT",
                rows=[["2026-09", "115,496,211"], ["2026-10", "152,306,418"]],
            ),
        ]
    )
    message = AssistantMessage(
        "msg_1", "assistant", datetime(2026, 10, 17, tzinfo=UTC), answer=answer
    )

    doc = _msg_to_doc(message)

    assert not _nested_lists(doc.answer)
    back = _msg_to_domain(doc)
    assert back.answer is not None and back.answer.parts[1].rows == [
        ["2026-09", "115,496,211"],
        ["2026-10", "152,306,418"],
    ]
