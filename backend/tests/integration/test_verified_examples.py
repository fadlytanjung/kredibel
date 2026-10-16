"""Verified examples in prompts (spec 016, T016-08, AC-016-9): a person's category correction
becomes an example; the next categorization in the same workspace sends it to the model; an
example from another workspace never reaches a prompt. Synthetic data only."""

from datetime import UTC, date, datetime
from decimal import Decimal as D

from app.agents.deps import PipelineDeps
from app.agents.labels import verified_examples
from app.domain.examples import Example
from app.domain.labels import AiDecision, LabelSubject, propose
from app.domain.models.bank_line import BankLine
from tests.fakes.embedder import FakeEmbedder
from tests.fakes.label_repository import FakeLabelRepository
from tests.integration.test_invoice_workflow import AUTH, _client, _deps

ORG = "org_1"
AT = datetime(2026, 7, 2, 9, 14, tzinfo=UTC)
GVF = "TRANSFER OUT GREEN VALLEY FARMS 0912"


def pipeline_of(deps) -> PipelineDeps:
    """What the workflow nodes get: the app's label store, learning policy and embedder."""
    return PipelineDeps(
        settings=deps.settings,
        run_repo=deps.run_repo,
        doc_repo=deps.doc_repo,
        month_repo=deps.month_repo,
        labels=deps.label_repo,
        learning=deps.learning,
        embedder=deps.embedder,
    )


async def test_ac016_9_a_correction_becomes_an_example_for_this_workspace_only():
    deps, _ = _deps()
    await deps.bank_lines.replace_document_lines(
        ORG,
        "doc_mar",
        [
            BankLine(
                tx_id="tx_gvf",
                doc_id="doc_mar",
                page=2,
                row_index=7,
                date=date(2026, 3, 12),
                month="2026-03",
                description=GVF,
                amount=D("-9850000.00"),
                balance=None,
                counterparty_name="GREEN VALLEY FARMS",
                category="SUPPLIER_PAYMENT",
                categorized_by="MODEL",
            )
        ],
    )
    label = propose(
        "CATEGORY",
        LabelSubject(display=GVF, doc_id="doc_mar", page_no=2, tx_id="tx_gvf"),
        AiDecision(value="SUPPLIER_PAYMENT", source="MODEL", at=AT, confidence=D("0.81")),
        policy=deps.learning,
        month="2026-03",
        example_text=GVF,
    )
    repo = deps.label_repo
    assert isinstance(repo, FakeLabelRepository)
    await repo.upsert(ORG, [label])
    pipeline = pipeline_of(deps)
    assert await verified_examples(pipeline, ORG, "CATEGORY", [GVF]) == [], "nothing decided yet"

    async with _client(deps) as client:
        res = await client.post(
            f"/api/labels/{label.label_id}/decision",
            headers=AUTH,
            json={"action": "CORRECT", "value": "INVENTORY_PURCHASE"},
        )
        assert res.status_code == 200, res.text
    assert await repo.has_examples(ORG, "CATEGORY")

    # A later line of the same supplier gets the person's decision as an example.
    rows = await verified_examples(
        pipeline, ORG, "CATEGORY", ["TRANSFER OUT GREEN VALLEY FARMS 1003"]
    )
    assert rows == [{"description": GVF, "category": "INVENTORY_PURCHASE"}]
    # An unrelated line gets none: below the similarity floor of the policy.
    assert await verified_examples(pipeline, ORG, "CATEGORY", ["PAYROLL JUNE STAFF"]) == []
    # Another workspace sees nothing of org_1's examples.
    assert await verified_examples(pipeline, "org_other", "CATEGORY", [GVF]) == []


async def test_ac016_9_an_example_from_another_workspace_is_dropped_before_the_prompt():
    deps, _ = _deps()
    pipeline = pipeline_of(deps)

    class LeakyLabels(FakeLabelRepository):
        async def has_examples(self, org_id: str, task: str) -> bool:
            return True

        async def nearest_examples(self, org_id, task, vector, limit):
            return [
                Example("org_other", "lbl_foreign", task, GVF, "RENT", 0.99),
                Example(org_id, "lbl_mine", task, GVF, "INVENTORY_PURCHASE", 0.95),
            ]

    pipeline.labels = LeakyLabels()
    pipeline.embedder = FakeEmbedder()
    rows = await verified_examples(pipeline, ORG, "CATEGORY", [GVF])
    assert rows == [{"description": GVF, "category": "INVENTORY_PURCHASE"}]
