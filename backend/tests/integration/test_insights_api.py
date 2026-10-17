"""The dashboard, money flow and cash flow through the API (spec 010, T010-02, AC-010-1, AC-010-5,
AC-010-6, AC-010-12…14). Synthetic March statement and invoice of "Sunrise Coffee Roasters"."""

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal as D

from app.domain.review_items import RecordFacts, month_items
from tests.fakes.document_reader import FakeDocumentReader
from tests.integration.test_invoice_workflow import AUTH, PDF, _client, _deps, _recorded
from tests.integration.test_month_workflow_reconcile import STATEMENT, _classify, _upload
from tests.integration.test_reading_workflow import _recorded_page


async def _books(client, deps) -> list[dict]:
    deps._reader = FakeDocumentReader(_classify, pages=_recorded_page, invoice_pages=_recorded)
    statement = await _upload(client, deps, STATEMENT, "march.pdf")
    await _upload(client, deps, PDF.read_bytes(), "invoice.pdf")
    return (await client.get("/api/bank-lines", params={"docId": statement}, headers=AUTH)).json()[
        "items"
    ]


def _cash(lines: list[dict]) -> tuple[D, D]:
    amounts = [D(ln["amount"]["amount"]) for ln in lines if ln["cashflowClass"] != "NON_CASH"]
    return sum((a for a in amounts if a > 0), D(0)), -sum((a for a in amounts if a < 0), D(0))


async def test_the_money_flow_balances_and_a_band_opens_its_lines():
    deps, _ = _deps()
    async with _client(deps) as client:
        lines = await _books(client, deps)
        flow = (
            await client.get("/api/money-flow", params={"period": "2026-03"}, headers=AUTH)
        ).json()
        gaap = (
            await client.get(
                "/api/money-flow",
                params={"period": "2026-03", "framework": "US_GAAP"},
                headers=AUTH,
            )
        ).json()
        by_client = (
            await client.get(
                "/api/money-flow",
                params={"period": "2026-03", "view": "COUNTERPARTIES"},
                headers=AUTH,
            )
        ).json()
        band = max(flow["links"], key=lambda link: D(link["value"]["amount"]))
        behind = (
            await client.get(
                "/api/bank-lines", params={"flow": band["id"], "period": "2026-03"}, headers=AUTH
            )
        ).json()

    assert (flow["period"], flow["view"], flow["framework"]) == ("2026-03", "STATEMENT", "IFRS")
    assert gaap["framework"] == "US_GAAP"
    for body in (flow, gaap, by_client):
        into: dict[str, D] = defaultdict(D)
        out: dict[str, D] = defaultdict(D)
        for link in body["links"]:
            into[link["target"]] += D(link["value"]["amount"])
            out[link["source"]] += D(link["value"]["amount"])
        for n in body["nodes"]:
            if n["column"] == "ACCOUNT":
                assert into[n["id"]] == out[n["id"]]
    money_in, _ = _cash(lines)
    sources = sum(
        D(n["value"]["amount"])
        for n in flow["nodes"]
        if n["column"] == "SOURCE" and n["id"] != "src:balance"
    )
    assert sources == money_in
    assert {n["column"] for n in by_client["nodes"]} == {"SOURCE", "ACCOUNT", "USE"}
    assert len(behind["items"]) == band["lineCount"] > 0
    assert sum(abs(D(ln["amount"]["amount"])) for ln in behind["items"]) == D(
        band["value"]["amount"]
    )


async def test_the_cash_flow_adds_up_from_opening_to_closing():
    deps, _ = _deps()
    async with _client(deps) as client:
        lines = await _books(client, deps)
        cash = (
            await client.get("/api/cash-flow", params={"period": "2026-03"}, headers=AUTH)
        ).json()
        bad = await client.get("/api/cash-flow", params={"period": "March"}, headers=AUTH)

    [march] = cash["months"]
    money_in, money_out = _cash(lines)
    assert (D(march["in"]["amount"]), D(march["out"]["amount"])) == (money_in, money_out)
    assert cash["balanced"] is True and cash["gaps"] == []
    steps = sum(D(v["amount"]) for v in cash["byActivity"].values())
    assert D(cash["opening"]["amount"]) + steps == D(cash["closing"]["amount"])
    assert D(march["closing"]["amount"]) == D(cash["closing"]["amount"])
    assert bad.status_code == 422


async def test_the_dashboard_previews_the_review_queue_of_its_period():
    deps, _ = _deps()
    async with _client(deps) as client:
        await _books(client, deps)
        await deps.review_items.replace_month_review_items(
            "org_1",
            "2026-03",
            month_items(
                month="2026-03",
                currency="IDR",
                risk_level="LOW",
                lines=[],
                records=[
                    RecordFacts(
                        f"inv_{n}", f"doc_{n}", "PURCHASE", f"BW-{n}", None, D("100.00"), "UNPAID"
                    )
                    for n in range(7)
                ],
                proposals=[],
                held=[],
            ),
            now=datetime(2026, 4, 2, tzinfo=UTC),
        )
        board = (await client.get("/api/dashboard", headers=AUTH)).json()

    kpis = {k["id"]: k for k in board["kpis"]}
    assert kpis["OPEN_REVIEW_ITEMS"]["value"] >= 7
    assert len(board["reviewPreview"]) == 5
    assert board["reviewPreview"][0]["kind"] in (
        "POSSIBLE_DUPLICATE",
        "PROPOSED_MATCH",
        "UNMATCHED_DOCUMENT",
    )
    assert [k["id"] for k in board["kpis"]][-2:] == ["OPEN_REVIEW_ITEMS", "DOCUMENTS_WAITING"]


async def test_the_dashboard_shows_the_period_figures_months_and_top_flows():
    deps, _ = _deps()
    async with _client(deps) as client:
        lines = await _books(client, deps)
        board = (await client.get("/api/dashboard", headers=AUTH)).json()
        queue = (await client.get("/api/review-items?status=OPEN", headers=AUTH)).json()["items"]

    assert (board["period"], board["periodMonths"]) == ("recent", ["2026-03"])
    kpis = {k["id"]: k for k in board["kpis"]}
    money_in, money_out = _cash(lines)
    assert D(kpis["MONEY_IN"]["value"]["amount"]) == money_in
    assert D(kpis["NET"]["value"]["amount"]) == money_in - money_out
    assert kpis["MONEY_IN"]["previous"] is None  # nothing before March
    assert "AUTO_MATCH_RATE" in kpis and kpis["DOCUMENTS_WAITING"]["value"] == 0
    assert kpis["OPEN_REVIEW_ITEMS"]["value"] == len(queue)  # every open item (docs/11 §6.2)
    assert [i["itemId"] for i in board["reviewPreview"]] == [i["itemId"] for i in queue][:5]
    [march] = board["months"]
    assert (
        march["month"],
        march["state"],
        march["statementsPresent"],
        march["statementsExpected"],
    ) == (
        "2026-03",
        "RECONCILED",
        1,
        1,
    )
    top = board["moneyFlowSummary"]
    assert 0 < len(top["topSources"]) <= 3 and 0 < len(top["topUses"]) <= 3


async def test_a_period_is_a_month_a_range_of_at_most_twelve_months_or_a_year():
    deps, _ = _deps()
    async with _client(deps) as client:
        await _books(client, deps)
        month = (await client.get("/api/dashboard?period=2026-03", headers=AUTH)).json()
        year = (await client.get("/api/dashboard?period=2026", headers=AUTH)).json()
        too_long = await client.get("/api/dashboard?period=2025-03..2026-03", headers=AUTH)
        reversed_range = await client.get("/api/cash-flow?period=2026-03..2026-01", headers=AUTH)
    assert month["periodMonths"] == ["2026-03"] and len(year["periodMonths"]) == 12
    assert too_long.status_code == 422 and reversed_range.status_code == 422
