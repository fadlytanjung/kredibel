"""Dashboard, money flow and cash flow routes (spec 010, T010-02; docs/10 §2.7).

Bodies only: every number is computed by InsightService from the workspace's statements.
"""

from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import ServiceProvider, org_of
from app.api.review_items import review_item_body
from app.core.auth import Principal
from app.domain.cash_flow import CashFlow
from app.domain.errors import ValidationProblem
from app.domain.money_flow import FlowNode, MoneyFlow
from app.domain.period import resolve_period
from app.services.insight_service import Dashboard, Kpi

PERIOD = (
    r"^(all|recent|\d{4}|\d{4}-Q[1-4]|\d{4}-(0[1-9]|1[0-2])"
    r"|\d{4}-(0[1-9]|1[0-2])\.\.\d{4}-(0[1-9]|1[0-2]))$"
)
Framework = Literal["IFRS", "US_GAAP"]
View = Literal["STATEMENT", "COUNTERPARTIES"]


def checked_period(period: str) -> str:
    """A period the pattern lets through but that is no period (a reversed range, a range of more
    than 12 months) is the caller's mistake, a 422."""
    try:
        resolve_period(period, ())
    except ValueError as error:
        raise ValidationProblem("period", str(error)) from error
    return period


def money(value: Decimal | None, currency: str) -> dict[str, str] | None:
    return None if value is None else {"amount": f"{value:.2f}", "currency": currency}


def node_body(n: FlowNode, currency: str) -> dict[str, Any]:
    body: dict[str, Any] = {
        "id": n.id,
        "column": n.column,
        "label": n.label,
        "value": money(n.value, currency),
    }
    if n.cashflow_class:
        body["cashflowClass"] = n.cashflow_class
    if n.statement_line:
        body["statementLine"] = n.statement_line
    return body


def money_flow_body(flow: MoneyFlow, currency: str, period: str) -> dict[str, Any]:
    return {
        "period": period,
        "view": flow.view,
        "framework": flow.framework,
        "nodes": [node_body(n, currency) for n in flow.nodes],
        "links": [
            {
                "id": link.id,
                "source": link.source,
                "target": link.target,
                "value": money(link.value, currency),
                "lineCount": link.line_count,
            }
            for link in flow.links
        ],
        "excludedHeld": money(flow.excluded_held, currency),
        "note": flow.note,
    }


def cash_flow_body(cash: CashFlow, currency: str, period: str) -> dict[str, Any]:
    return {
        "period": period,
        "framework": cash.framework,
        "opening": money(cash.opening, currency),
        "closing": money(cash.closing, currency),
        "balanced": cash.balanced,
        "gapReason": None,
        "gaps": [
            {
                k: v
                for k, v in (
                    ("kind", g.kind),
                    ("month", g.month),
                    ("account", g.account),
                    ("amount", money(g.amount, currency)),
                )
                if v is not None
            }
            for g in cash.gaps
        ],
        "months": [
            {
                k: v
                for k, v in (
                    ("month", m.month),
                    ("in", money(m.money_in, currency)),
                    ("out", money(m.money_out, currency)),
                    ("net", money(m.net, currency)),
                    ("closing", money(m.closing, currency)),
                    ("riskLevel", m.risk_level),
                )
                if v is not None
            }
            for m in cash.months
        ],
        "byActivity": {name: money(v, currency) for name, v in cash.by_activity.items()},
        "byLine": [
            {
                k: v
                for k, v in (
                    ("line", x.line),
                    ("category", x.category),
                    ("label", x.label),
                    ("cashflowClass", x.cashflow_class),
                    ("amount", money(x.amount, currency)),
                )
                if v is not None
            }
            for x in cash.by_line
        ],
        "note": cash.note,
    }


def _kpi_value(kpi: Kpi, value: Decimal | int | None, currency: str) -> Any:
    if value is None:
        return None
    if kpi.kind == "money":
        return money(Decimal(value), currency)
    if kpi.kind == "rate":
        return str(value)
    return int(value)


def dashboard_body(d: Dashboard) -> dict[str, Any]:
    c = d.currency
    return {
        "period": d.period.key,
        "periodMonths": list(d.period.months),
        "kpis": [
            {
                "id": k.id,
                "value": _kpi_value(k, k.value, c),
                "previous": _kpi_value(k, k.previous, c),
            }
            for k in d.kpis
        ],
        "months": [
            {
                k: v
                for k, v in (
                    ("month", m.month),
                    ("state", m.state),
                    ("statementsPresent", m.statements_present),
                    ("statementsExpected", m.statements_expected),
                    ("riskLevel", m.risk_level),
                    ("autoMatchRate", m.auto_match_rate),
                    ("moneyIn", money(m.money_in, c)),
                    ("moneyOut", money(m.money_out, c)),
                )
                if v is not None
            }
            for m in d.months
        ],
        "alerts": [
            {
                k: v
                for k, v in (
                    ("severity", a.severity),
                    ("title", a.title),
                    ("month", a.month),
                    ("findingId", a.finding_id),
                    ("link", a.link),
                )
                if v is not None
            }  # fmt: skip
            for a in d.alerts
        ],
        "moneyFlowSummary": {
            "topSources": [node_body(n, c) for n in d.top_sources],
            "topUses": [node_body(n, c) for n in d.top_uses],
        },
        "reviewPreview": [review_item_body(i) for i in d.review_preview],
    }


def create_insights_router(provider: ServiceProvider, workspace_dep: Any) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["insight"])

    @router.get("/dashboard")
    async def get_dashboard(
        period: str = Query(default="recent", pattern=PERIOD),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        return dashboard_body(
            await provider.insight_service.dashboard(
                org_of(principal), period=checked_period(period)
            )
        )

    @router.get("/money-flow")
    async def get_money_flow(
        period: str = Query(default="all", pattern=PERIOD),
        view: View = Query(default="STATEMENT"),
        framework: Framework | None = Query(default=None),
        account_id: str | None = Query(default=None, alias="accountId"),
        show_transfers: bool = Query(default=False, alias="showTransfers"),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        flow, currency, resolved = await provider.insight_service.money_flow(
            org_of(principal),
            period=checked_period(period),
            view=view,
            framework=framework,
            account_id=account_id,
            show_transfers=show_transfers,
        )
        return money_flow_body(flow, currency, resolved.key)

    @router.get("/cash-flow")
    async def get_cash_flow(
        period: str = Query(default="all", pattern=PERIOD),
        framework: Framework | None = Query(default=None),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        cash, currency, resolved = await provider.insight_service.cash_flow(
            org_of(principal), period=checked_period(period), framework=framework
        )
        return cash_flow_body(cash, currency, resolved.key)

    return router
