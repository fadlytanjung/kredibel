"""The dashboard's to-do figures (docs/11 §6.2, AC-010-1): "To review" counts every open review
item, as the sidebar and the queue do, whatever period the figures are for, and the preview is the
queue's first five. Synthetic data only (S1)."""

from tests.integration import scenario_books as books
from tests.integration.test_invoice_workflow import AUTH, _client


async def test_to_review_counts_the_whole_queue_whatever_the_period():
    deps = books.books_deps()
    async with _client(deps) as client:
        await books.seed(deps, "S1", books.load_truth("S1"))
        await books.run_months(deps)
        queue = (await client.get("/api/review-items?status=OPEN&limit=500", headers=AUTH)).json()
        board = (await client.get("/api/dashboard?period=2026-06", headers=AUTH)).json()

    items = queue["items"]
    assert {i["month"] for i in items} - {"2026-06", None}, "S1 has open items outside June"
    kpis = {k["id"]: k["value"] for k in board["kpis"]}
    assert kpis["OPEN_REVIEW_ITEMS"] == len(items)
    assert [i["itemId"] for i in board["reviewPreview"]] == [i["itemId"] for i in items][:5]
