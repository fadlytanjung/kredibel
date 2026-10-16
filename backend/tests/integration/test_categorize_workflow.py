"""Categorization end to end (spec 007, AC-007-1): rules decide first, the model the rest in
cached batches, unsure answers stay UNKNOWN; the cash-flow class comes from the framework."""

import io
import re

from app.adapters.cloud_tasks import InlineTaskQueue
from app.domain.reading import TransactionItem
from app.main import create_app
from tests.fakes.bank_line_repository import FakeBankLineRepository
from tests.fakes.document_reader import FakeDocumentReader
from tests.fakes.document_repository import FakeDocumentRepository
from tests.integration.test_reading_workflow import FIXTURES, TRUTH, _deps, _recorded_page


def _model(item: TransactionItem) -> tuple[str, float]:
    """A recorded categorizer: sure about transfers in, unsure about anything else."""
    if item.direction == "in" and "TRANSFER" in item.description:
        return "SALES_RECEIPT", 0.92
    if "CORNER BAKERY" in item.description:
        return "OTHER_OPERATING_EXPENSE", 0.81
    return "OTHER_OPERATING_EXPENSE", 0.3


async def test_lines_are_categorized_by_rules_then_the_model():
    from httpx import ASGITransport, AsyncClient

    lines = FakeBankLineRepository()
    deps = _deps(lines, FakeDocumentRepository())

    def typed_page(page: int):
        kind = "STATEMENT_SUMMARY" if page == 1 else "STATEMENT_TRANSACTIONS"
        return _recorded_page(page).model_copy(
            update={"page_type": kind, "page_type_confidence": 0.62 if page == 1 else 0.98}
        )

    reader = FakeDocumentReader(pages=typed_page, categories=_model)
    deps._reader = reader
    app = create_app(deps.settings, deps=deps)
    pdf = (FIXTURES / "acb-2026-03.pdf").read_bytes()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/documents",
            headers={"Authorization": "Bearer owner"},
            files={"file": ("acb.pdf", io.BytesIO(pdf), "application/pdf")},
        )
        queue = deps.task_queue
        assert isinstance(queue, InlineTaskQueue)
        await queue.drain()
        doc_id = res.json()["docId"]
        body = (
            await client.get(
                "/api/bank-lines",
                params={"docId": doc_id},
                headers={"Authorization": "Bearer owner"},
            )
        ).json()
        # AC-016-4: every read page has its extraction, served after the workspace check.
        page_one = await client.get(
            f"/api/documents/{doc_id}/pages/1/extraction.md",
            headers={"Authorization": "Bearer owner"},
        )
        missing = await client.get(
            f"/api/documents/{doc_id}/pages/99/extraction.md",
            headers={"Authorization": "Bearer owner"},
        )

    stored = await lines.list_lines("org_1", doc_id=doc_id)
    truth = {(r["description"], r["date"]): r["category"] for r in TRUTH["rows"]}
    by = {ln.categorized_by for ln in stored}
    assert by <= {"RULE", "MODEL", "NONE"} and "RULE" in by and "MODEL" in by
    for ln in stored:
        if ln.categorized_by == "RULE":  # every rule decision agrees with the truth
            assert ln.category == truth[(ln.description, ln.date.isoformat())], ln.description
    payroll = next(ln for ln in stored if ln.description.startswith("PAYROLL"))
    assert (payroll.category, payroll.cashflow_class) == ("PAYROLL", "OPERATING")
    loan = next(ln for ln in stored if ln.description.startswith("LOAN INSTALLMENT"))
    assert (loan.category, loan.cashflow_class) == ("LOAN_REPAYMENT", "FINANCING")
    deposit = next(ln for ln in stored if ln.description == "CASH DEPOSIT")
    assert "CASH_DEPOSIT" in deposit.risk_tags  # a tag-only rule; the category is the model's
    sale = next(ln for ln in stored if ln.description.startswith("INSTANT TRANSFER IN DAYBREAK"))
    assert (sale.category, sale.categorized_by) == ("SALES_RECEIPT", "MODEL")
    unsure = next(ln for ln in stored if "SWIFT COURIER" in ln.description)
    assert (unsure.category, unsure.categorized_by, unsure.cashflow_class) == (
        "UNKNOWN",
        "NONE",
        "UNCLASSIFIED",
    )
    assert page_one.status_code == 200, page_one.text
    assert page_one.headers["content-type"].startswith("text/markdown")
    md = page_one.text
    assert md.startswith("# acb.pdf, page 1 of ") and "Document type: BANK_STATEMENT" in md
    assert "| Record | Field | Readings | Model | Text layer |" in md and "## Witness text" in md
    assert not re.search(r"\d{8,}", md), "no account or ID number in clear"
    assert missing.status_code == 404
    assert "Page type: STATEMENT_SUMMARY (0.62)" in md.splitlines()
    # Every read page is a PAGE_TYPE label; the low one asks a person (learning.v1: below 0.80).
    pages = await deps.label_repo.list_labels("org_1", task="PAGE_TYPE", limit=None)
    by_page = {lb.subject.page_no: lb for lb in pages}
    assert by_page[1].final_value == "STATEMENT_SUMMARY" and by_page[1].needs_check
    assert all(
        lb.final_value == "STATEMENT_TRANSACTIONS" for n, lb in by_page.items() if (n or 0) > 1
    )
    assert by_page[1].ai.prompt_version == "statement_page@test" and by_page[1].extraction_url
    # AC-016-1: every category the run decided is a label, with its source and confidence.
    labels = await deps.label_repo.list_labels("org_1", task="CATEGORY", limit=None)
    by_tx = {lb.subject.tx_id: lb for lb in labels}
    assert by_tx[sale.tx_id].ai.source == "MODEL" and by_tx[sale.tx_id].ai.model == "fake-model"
    assert by_tx[sale.tx_id].ai.run_id and by_tx[sale.tx_id].final_value == "SALES_RECEIPT"
    assert by_tx[payroll.tx_id].ai.source == "RULE" and by_tx[payroll.tx_id].ai.model is None
    assert unsure.tx_id not in by_tx, "an undecided line is no label yet"
    assert all(lb.status == "AI_PROPOSED" and lb.month == "2026-03" for lb in labels)
    assert (
        by_tx[sale.tx_id].extraction_url
        == f"/api/documents/{doc_id}/pages/{sale.page}/extraction.md"
    )
    api_sale = next(i for i in body["items"] if i["txId"] == sale.tx_id)
    assert (api_sale["category"], api_sale["cashflowClass"], api_sale["categorizedBy"]) == (
        "SALES_RECEIPT",
        "OPERATING",
        "MODEL",
    )

    calls = [c for c in reader.calls if c[0] == "categorize"]
    assert len(calls) == 1 and calls[0][1] < len(stored)  # one batch, only what rules left
    # The run records the categorizer's model beside its tokens (docs/23 §5.1).
    runs = await deps.run_repo.list_by_target("org_1", doc_id)
    (stage,) = [s for r in runs for s in r.stages if s.node == "categorize_bank_lines"]
    assert stage.model == "fake-model" and stage.tokens_in
    await deps.document_workflow_runner("org_1", doc_id, "run_again", 1)
    assert [c for c in reader.calls if c[0] == "categorize"] == calls  # served from the cache
