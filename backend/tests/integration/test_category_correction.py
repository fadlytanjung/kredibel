"""User category choices are audited and survive the next extraction/categorization run."""

from tests.fakes.bank_line_repository import FakeBankLineRepository
from tests.integration.test_document_first_reconciliation import drain
from tests.integration.test_invoice_workflow import AUTH, _client
from tests.integration.test_month_workflow_reconcile import STATEMENT, _upload
from tests.support.reconciliation_demo import demo_deps


async def test_category_correction_recomputes_figures_and_survives_rereading():
    deps = demo_deps()
    async with _client(deps) as client:
        doc = await _upload(client, deps, STATEMENT, "statement.pdf")
        lines = (await client.get("/api/bank-lines", headers=AUTH)).json()["items"]
        line = next(ln for ln in lines if ln["description"].startswith("PAYROLL"))
        result = await client.patch(
            f"/api/bank-lines/{line['txId']}",
            json={"category": "OTHER_OPERATING_EXPENSE"},
            headers=AUTH,
        )
        assert result.status_code == 200, result.text
        assert result.json()["categorizedBy"] == "USER"
        await drain(deps)
        await deps.document_workflow_runner("org_1", doc, "reread", 1)
        await drain(deps)
        updated = await deps.bank_lines.get_line("org_1", line["txId"])
        assert updated is not None
        assert (updated.category, updated.categorized_by) == ("OTHER_OPERATING_EXPENSE", "USER")
        assert isinstance(deps.bank_lines, FakeBankLineRepository)
        assert deps.bank_lines.events[-1].type == "CATEGORY_CHANGED"
        month = (await client.get("/api/months/2026-03", headers=AUTH)).json()
        assert "category:OTHER_OPERATING_EXPENSE" in month["figures"]


async def test_category_correction_checks_membership_vocabulary_direction_and_workspace():
    deps = demo_deps()
    async with _client(deps) as client:
        await _upload(client, deps, STATEMENT, "statement.pdf")
        lines = (await client.get("/api/bank-lines", headers=AUTH)).json()["items"]
        debit = next(ln for ln in lines if ln["amount"]["amount"].startswith("-"))
        path = f"/api/bank-lines/{debit['txId']}"
        for category in ("MADE_UP", "SALES_RECEIPT"):
            result = await client.patch(path, json={"category": category}, headers=AUTH)
            assert result.status_code == 422
        assert (await client.patch(path, json={"category": "RENT"})).status_code == 401
        result = await client.patch(
            "/api/bank-lines/tx_missing", json={"category": "RENT"}, headers=AUTH
        )
        assert result.status_code == 404
