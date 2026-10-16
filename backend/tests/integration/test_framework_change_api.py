"""Changing the accounting framework (spec 016, T016-06, AC-016-8): every bank line's cash-flow
class is derived again from categories.v1.yaml, categories stay, and each month runs once.
Synthetic data only."""

from datetime import date
from decimal import Decimal as D

from app.domain.models.bank_line import BankLine
from app.domain.models.run import RunKind
from tests.integration.test_invoice_workflow import AUTH, _client, _deps

ORG = "org_1"


def line(tx: str, month: str, amount: str, category: str, cashflow: str) -> BankLine:
    day = date(int(month[:4]), int(month[5:]), 10)
    return BankLine(
        tx_id=tx,
        doc_id=f"doc_{month}",
        page=1,
        row_index=int(tx[-1]),
        date=day,
        month=month,
        description=tx.upper(),
        amount=D(amount),
        balance=None,
        category=category,
        cashflow_class=cashflow,
        categorized_by="RULE",
    )


async def test_ac016_8_the_framework_change_re_derives_classes_and_runs_each_month_once():
    deps, _ = _deps()
    await deps.bank_lines.replace_document_lines(
        ORG,
        "doc_2026-02",
        [line("tx_1", "2026-02", "-2000000.00", "INTEREST_PAID", "FINANCING")],
    )
    await deps.bank_lines.replace_document_lines(
        ORG,
        "doc_2026-03",
        [
            line("tx_2", "2026-03", "150000.00", "INTEREST_RECEIVED", "INVESTING"),
            line("tx_3", "2026-03", "-18000000.00", "PAYROLL", "OPERATING"),
        ],
    )
    async with _client(deps) as client:
        res = await client.patch(
            "/api/workspace", json={"profile": {"accountingFramework": "US_GAAP"}}, headers=AUTH
        )
        assert res.status_code == 200, res.text
        assert res.json()["profile"]["accountingFramework"] == "US_GAAP"

    by_tx = {ln.tx_id: ln for ln in await deps.bank_lines.list_lines(ORG, limit=100)}
    assert (by_tx["tx_1"].category, by_tx["tx_1"].cashflow_class) == ("INTEREST_PAID", "OPERATING")
    assert (by_tx["tx_2"].category, by_tx["tx_2"].cashflow_class) == (
        "INTEREST_RECEIVED",
        "OPERATING",
    )
    assert by_tx["tx_3"].cashflow_class == "OPERATING"
    assert all(ln.categorized_by == "RULE" for ln in by_tx.values()), "categories untouched"
    runs = await deps.run_repo.list_runs(ORG, kind=RunKind.MONTH, limit=50)
    assert sorted({r.target for r in runs}) == ["2026-02", "2026-03"]

    # Saving the profile again without a change starts nothing new.
    before = len(await deps.run_repo.list_runs(ORG, kind=RunKind.MONTH, limit=50))
    async with _client(deps) as client:
        await client.patch(
            "/api/workspace", json={"profile": {"accountingFramework": "US_GAAP"}}, headers=AUTH
        )
        await client.patch("/api/workspace", json={"name": "Sunrise Coffee"}, headers=AUTH)
    assert len(await deps.run_repo.list_runs(ORG, kind=RunKind.MONTH, limit=50)) == before
