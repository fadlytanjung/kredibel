"""Corrected values reach the books (spec 023, AC-023-8): a value a person corrects on the Labels
page changes the line and reconciles its month, as the review queue does; a value corrected anywhere
is a person's decision on its label. Synthetic data only."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal as D

from app.domain.label_sync import line_records, value_labels
from app.domain.labels import AiDecision, LabelSubject, LearningPolicy, propose
from tests.integration.test_invoice_workflow import AUTH, _client, _deps
from tests.integration.test_labels_api import ORG, line

AT = datetime(2026, 7, 2, 9, 14, tzinfo=UTC)
CONFLICT = {
    "amount": {
        "status": "CONFLICT",
        "page": 1,
        "bbox": None,
        "raw": {"GEMINI": "24,500,000.00", "TEXT_LAYER": "24,800,000.00"},
    }
}


async def test_ac023_8_a_value_corrected_on_the_labels_page_changes_the_line_and_its_month():
    deps, _ = _deps()
    await deps.bank_lines.replace_document_lines(
        ORG,
        "doc_may",
        [
            replace(
                line("tx_1", "-24500000.00", "Roastline Equipment Service", 6), consensus=CONFLICT
            )
        ],
    )
    label = propose(
        "FIELD_VALUE",
        LabelSubject(
            display="Row 6 · amount", doc_id="doc_may", page_no=1, field="amount", tx_id="tx_1"
        ),
        AiDecision(value="24,500,000.00", source="MODEL", at=AT),
        policy=deps.learning,
        month="2026-05",
    )
    [stored] = await deps.label_repo.upsert(ORG, [label])

    async with _client(deps) as client:
        bad = await client.post(
            f"/api/labels/{stored.label_id}/decision",
            headers=AUTH,
            json={"action": "CORRECT", "value": "about 24.8 million"},
        )
        res = await client.post(
            f"/api/labels/{stored.label_id}/decision",
            headers=AUTH,
            json={"action": "CORRECT", "value": "24800000.00"},
        )

    assert bad.status_code == 422
    assert res.status_code == 200, res.text
    fixed = await deps.bank_lines.get_line(ORG, "tx_1")
    assert fixed is not None and fixed.amount == D("-24800000.00")
    assert "amount" in fixed.corrected_fields
    months = {m.month: m for m in await deps.month_repo.list(ORG)}
    assert months["2026-05"].dirty


def test_ac023_8_a_value_a_person_corrected_elsewhere_is_their_decision_on_its_label():
    corrected = replace(
        line("tx_1", "-24800000.00", "Roastline Equipment Service", 6),
        consensus=CONFLICT,
        corrected_fields=["amount"],
        corrected_by="u-1",
        corrected_at=AT,
    )
    [label] = value_labels(
        "doc_may",
        "statement.pdf",
        line_records([corrected]),
        decision=lambda value: AiDecision(value=value, source="MODEL", at=AT),
        policy=LearningPolicy(needs_check_below={}),
    )
    assert label.status == "CORRECTED" and label.final_value == "24800000.00"
    assert label.decided_by == "u-1" and not label.needs_check
