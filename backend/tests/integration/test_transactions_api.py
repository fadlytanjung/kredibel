"""The Transactions table through the API on S1 (spec 024, AC-024-6): every bank line of the month,
by date, with both frameworks' classes, its subledger and what it is matched to. Synthetic data."""

from tests.integration import scenario_books as books
from tests.integration.test_invoice_workflow import AUTH, _client


async def test_ac024_6_a_month_lists_every_bank_line_with_its_classes_and_records():
    truth = books.load_truth("S1")
    deps = books.books_deps()
    async with _client(deps) as client:
        await books.seed(deps, "S1", truth)
        await books.run_months(deps)
        res = await client.get("/api/transactions", params={"month": "2026-03"}, headers=AUTH)
        bad = await client.get("/api/transactions", params={"month": "March"}, headers=AUTH)

    assert res.status_code == 200, res.text
    assert bad.status_code == 422
    items = res.json()["items"]
    lines = [ln for ln in await deps.bank_lines.list_lines(books.ORG, month="2026-03", limit=500)]
    assert len(items) == len(lines) > 0
    assert [i["date"] for i in items] == sorted(i["date"] for i in items)
    for item in items:
        assert set(item["cashflow"]) == {"ifrs", "usGaap"}
        assert item["reading"] in ("AGREED", "CONFLICT", "SINGLE_SOURCE", "MISSING")
        assert item["amount"]["currency"] == "IDR"
    kinds = {r["kind"] for i in items for r in i["match"]["records"]}
    assert {"INVOICE", "LEDGER_ENTRY"} <= kinds
    sale = next(i for i in items if i["category"] == "SALES_RECEIPT" and i["match"]["records"])
    assert (sale["pnlLine"], sale["subledger"]) == ("Revenue", "Sales")
    assert sale["match"]["records"][0]["docId"].startswith("doc_")
