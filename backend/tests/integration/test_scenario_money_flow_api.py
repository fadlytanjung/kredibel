"""Where S1's money came from and went (spec 010, T010-07; AC-010-8): the top sources and uses of
the half-year equal `truth.json.expectedFlows`, read through the API. Synthetic data only."""

import unicodedata
from decimal import Decimal

from tests.integration import scenario_books as books
from tests.integration.test_invoice_workflow import AUTH, _client


def _plain(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text)
    return " ".join("".join(c for c in folded if not unicodedata.combining(c)).casefold().split())


def _by_value(nodes: list[dict]) -> list[dict]:
    return sorted(nodes, key=lambda n: (-Decimal(n["value"]["amount"]), n["label"]))


async def test_ac010_8_s1_top_sources_and_uses_equal_the_truth():
    truth = books.load_truth("S1")
    deps = books.books_deps()
    async with _client(deps) as client:
        await books.seed(deps, "S1", truth)
        await books.run_months(deps)
        res = await client.get(
            "/api/money-flow",
            params={"period": "2026-01..2026-06", "view": "COUNTERPARTIES"},
            headers=AUTH,
        )
        assert res.status_code == 200, res.text
        flow = res.json()
        dashboard = await client.get(
            "/api/dashboard", params={"period": "2026-01..2026-06"}, headers=AUTH
        )
        assert dashboard.status_code == 200, dashboard.text

    assert (flow["period"], flow["view"]) == ("2026-01..2026-06", "COUNTERPARTIES")
    clients = _by_value(
        [n for n in flow["nodes"] if n["column"] == "SOURCE" and n["id"].startswith("src:client:")]
    )
    uses = _by_value([n for n in flow["nodes"] if n["column"] == "USE" and n["id"] != "use:KEPT"])
    expected = truth["expectedFlows"]
    assert [_plain(n["label"]) for n in clients[:2]] == [_plain(s) for s in expected["topSources"]]
    assert [n["label"] for n in uses[:2]] == expected["topUses"]
    assert flow["excludedHeld"]["amount"] == "0.00"
