"""Deterministic read-only P&L answer; no generated numbers are published (AC-018-6)."""

import re
from decimal import Decimal

from app.domain.models.assistant import AnswerPart, CitationRef, GroundingRef, MessageAnswer
from app.domain.profit_loss import ProfitLoss


def is_profit_question(question: str) -> bool:
    return bool(
        re.search(
            r"\b(profit|p\s*&\s*l|pnl|income statement|laba rugi|revenue|omset|pendapatan)\b",
            question,
            re.I,
        )
    )


def report_period(question: str, scope: str) -> str:
    explicit = re.search(r"\b\d{4}(?:-Q[1-4]|-(?:0[1-9]|1[0-2]))?\b", question)
    if explicit:
        return explicit.group()
    return scope if re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", scope) else "recent"


def profit_loss_answer(report: ProfitLoss) -> MessageAnswer:
    cash = report.basis == "CASH"
    coverage = (
        "Cash-basis P&L from your categorized bank lines, by subledger label; no ledger export "
        "has been imported, so this is not an accrual report."
        if cash
        else "Accrual management P&L from imported posted ledger entries only."
    )
    if report.status == "UNAVAILABLE":
        text = (
            "Profit and loss is unavailable for this period. Upload bank statements for it, or "
            "a posted general ledger with account classifications."
            if cash
            else "Profit and loss is unavailable for this period. Add a posted general ledger with "
            "currency and account classifications. Bank cash movements cannot establish profit."
        )
    elif report.status == "PARTIAL":
        text = (
            "This is a partial report. Review excluded entries and ledger gaps "
            "before using its totals."
        )
    else:
        text = (
            "These totals cover imported activity; they do not certify that "
            "the company books are complete."
        )
    parts = [AnswerPart(type="text", text=f"{coverage}\n{text}\nPeriod: {report.period}")]
    citations = []
    chart_rows: list[list[str]] = []
    if any(line.amount is not None for line in report.lines):
        rows = []
        amounts = [abs(line.amount) for line in report.lines if line.amount is not None]
        max_val = max(amounts, default=Decimal(1)) or Decimal(1)
        for line in report.lines:
            label = line.id.replace("_", " ").capitalize()
            if line.amount is not None:
                rows.append([label, f"{line.amount:.2f} {report.currency} [[{line.fact_id}]]"])
                citations.append(CitationRef(ref=line.fact_id, label=label))
                pct = f"{int(abs(line.amount) / max_val * 100)}%"
                chart_rows.append([label, f"{line.amount:,.2f} {report.currency}", pct])
        parts.append(AnswerPart(type="table", columns=["P&L line", "Amount"], rows=rows))
    parts.append(
        AnswerPart(
            type="chart",
            chart="PROFIT_LOSS",
            rows=chart_rows if chart_rows else None,
            query={"period": report.period, "target": "profit-loss"},
        )
    )
    return MessageAnswer(
        parts=parts,
        citations=citations,
        grounding=GroundingRef(verdict="TEMPLATE", citations=[c.ref for c in citations]),
        tools_used=["get_profit_loss"],
    )
