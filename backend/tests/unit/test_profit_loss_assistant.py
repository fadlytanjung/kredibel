"""AC-018-6: same deterministic report, decimal facts, scoped period, no model arithmetic."""

from app.services.profit_loss_answer import is_profit_question, profit_loss_answer, report_period
from tests.unit.test_profit_loss import report, row


def test_ac018_6_scoped_period_and_no_invented_empty_profit():
    assert is_profit_question("Show my P&L chart")
    assert is_profit_question("What is our profit and loss?")
    assert not is_profit_question("Which invoices are unpaid?")
    assert report_period("Show profit", "2026-03") == "2026-03"
    assert report_period("P&L for 2026-Q2", "2026-03") == "2026-Q2"
    answer = profit_loss_answer(report([]))
    assert answer.grounding is not None
    assert answer.parts[0].text is not None
    assert answer.grounding.verdict == "TEMPLATE"
    assert "unavailable" in answer.parts[0].text.lower()
    assert not any(p.type == "table" for p in answer.parts)


def test_ac018_6_tool_facts_match_api_report_and_include_coverage():
    result = report([row("sales", credit="100.10"), row("bank", debit="100.10")])
    answer = profit_loss_answer(result)
    table = next(p for p in answer.parts if p.type == "table")
    assert table.rows is not None
    assert any("100.10" in cell for cells in table.rows for cell in cells)
    assert answer.tools_used == ["get_profit_loss"]
    assert {c.ref for c in answer.citations} == {line.fact_id for line in result.lines}
    assert answer.parts[-1].chart == "PROFIT_LOSS"
    assert answer.parts[-1].rows is not None
    assert any("Revenue" in r[0] for r in answer.parts[-1].rows)
    assert answer.parts[-1].query is not None
    assert answer.parts[-1].query["period"] == "2026-03"
