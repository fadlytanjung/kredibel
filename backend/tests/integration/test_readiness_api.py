"""The loan readiness report through the API (spec 025, AC-025-1…3, AC-025-5): computed from the
reconciled month, the open findings and the review queue; one month of statements is not enough to
show a lender. Synthetic March statement and invoice of "Sunrise Coffee Roasters"."""

from decimal import Decimal as D

from app.domain.findings import Evidence, Finding
from tests.integration.test_insights_api import _books, _cash
from tests.integration.test_invoice_workflow import AUTH, _client, _deps


def _edited_statement(month: str) -> Finding:
    return Finding(
        finding_id="fnd_a01_march",
        code="A01_RUNNING_BALANCE_BREAK",
        category="ARITHMETIC",
        severity="CRITICAL",
        title="The running balance breaks on page 1",
        facts={},
        evidence=[Evidence(doc_id="doc_st", page=1)],
        scope="MONTH",
        month=month,
        next_steps=["Ask the bank for the original statement."],
    )


async def test_ac025_1_one_reconciled_month_is_not_ready_and_says_why():
    deps, _ = _deps()
    async with _client(deps) as client:
        lines = await _books(client, deps)
        report = (await client.get("/api/readiness", headers=AUTH)).json()
        queue = (await client.get("/api/review-items?status=OPEN", headers=AUTH)).json()["items"]

    assert report["workspace"] == "Sunrise Coffee Roasters"
    assert (report["currency"], report["framework"], report["period"]) == ("IDR", "IFRS", "all")
    assert report["level"] == "NOT_READY"
    checks = {c["id"]: c for c in report["checks"]}
    assert list(checks) == ["HISTORY", "COVERAGE", "RECONCILED", "FINDINGS", "REVIEW", "CASH"]
    assert (checks["HISTORY"]["status"], checks["HISTORY"]["count"]) == ("FAIL", 1)
    assert checks["HISTORY"]["threshold"] == "3"
    assert checks["COVERAGE"]["status"] == "PASS"
    assert checks["REVIEW"]["count"] == len(queue)

    money_in, money_out = _cash(lines)
    [march] = report["months"]
    assert march["month"] == "2026-03"
    assert (D(march["moneyIn"]["amount"]), D(march["moneyOut"]["amount"])) == (money_in, money_out)
    assert march["reconciled"] is True
    totals = report["totals"]
    assert totals["months"] == 1
    assert D(totals["net"]["amount"]) == money_in - money_out
    assert D(totals["averageIn"]["amount"]) == money_in
    assert {d["type"] for d in report["documents"]} >= {"BANK_STATEMENT"}


async def test_ac025_3_an_open_critical_finding_fails_with_its_link_and_next_step():
    deps, _ = _deps()
    async with _client(deps) as client:
        await _books(client, deps)
        await deps.findings.replace_month_findings(
            "org_1", "2026-03", [_edited_statement("2026-03")], run_id=None
        )
        report = (await client.get("/api/readiness?period=2026-03", headers=AUTH)).json()

    found = next(c for c in report["checks"] if c["id"] == "FINDINGS")
    assert found["status"] == "FAIL"
    assert found["months"] == ["2026-03"]
    [a01] = [f for f in found["findings"] if f["code"] == "A01_RUNNING_BALANCE_BREAK"]
    assert a01["link"] == "/risk/fnd_a01_march"
    assert a01["nextStep"] == "Ask the bank for the original statement."
    assert report["period"] == "2026-03"


async def test_ac025_5_a_workspace_without_statements_has_nothing_to_show():
    deps, _ = _deps()
    async with _client(deps) as client:
        report = (await client.get("/api/readiness", headers=AUTH)).json()
        bad = await client.get("/api/readiness?period=March", headers=AUTH)

    assert report["level"] == "NOT_READY"
    assert report["months"] == [] and report["clients"] == []
    assert report["totals"]["averageIn"] is None
    assert bad.status_code == 422
