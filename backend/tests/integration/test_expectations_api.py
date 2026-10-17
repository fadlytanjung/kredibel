"""The person's goal and expectations (spec 024, AC-024-4, AC-024-5): saved on the workspace, and
compared with each reconciled month's money in and out. Synthetic data only."""

from datetime import UTC, datetime

from app.domain.models.month import Month, MonthState
from tests.integration.test_invoice_workflow import AUTH, _client, _deps


def _month(month: str, state: MonthState, money_in: str, money_out: str) -> Month:
    def fact(name: str, value: str) -> dict[str, object]:
        return {"value": value, "factId": f"fact:{month}:{name}", "inputs": []}

    return Month(
        month=month,
        state=state,
        dirty=False,
        generation=1,
        updated_at=datetime(2026, 10, 1, tzinfo=UTC),
        figures={"moneyIn": fact("money_in", money_in), "moneyOut": fact("money_out", money_out)},
    )


async def test_ac024_4_5_the_goal_and_expectations_are_saved_and_compared():
    deps, _ = _deps()
    await deps.month_repo.save(
        "org_1", _month("2026-08", MonthState.RECONCILED, "160423200.00", "152306418.00")
    )
    await deps.month_repo.save("org_1", _month("2026-09", MonthState.COLLECTING, "1.00", "1.00"))
    async with _client(deps) as client:
        bad = await client.patch(
            "/api/workspace",
            headers=AUTH,
            json={"expectations": [{"month": "2026-08", "moneyIn": "-5"}]},
        )
        saved = await client.patch(
            "/api/workspace",
            headers=AUTH,
            json={
                "goal": "CHECK_EXPECTATIONS",
                "expectations": [
                    {"month": "2026-09", "moneyIn": "150000000.00"},
                    {"month": "2026-08", "moneyIn": "160000000.00", "moneyOut": "120000000.00"},
                ],
            },
        )
        body = (await client.get("/api/expectations", headers=AUTH)).json()

    assert bad.status_code == 422
    assert saved.status_code == 200, saved.text
    workspace = saved.json()
    assert workspace["goal"] == "CHECK_EXPECTATIONS"
    assert [e["month"] for e in workspace["expectations"]] == ["2026-08", "2026-09"]
    aug, sep = body["months"]
    assert aug["moneyIn"]["status"] == "AS_EXPECTED"
    assert aug["moneyOut"] == {
        "expected": "120000000.00",
        "actual": "152306418.00",
        "difference": "32306418.00",
        "status": "DIFFERENT",
    }
    assert sep["moneyIn"]["status"] == "WAITING" and sep["moneyOut"] is None
    assert body["tolerance"] == "0.05"
