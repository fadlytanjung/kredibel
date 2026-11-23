"""The loan readiness report (spec 025, AC-025-1…3; ADR-028). A body only: every figure, check and
level comes from ReadinessService and domain/readiness.py. Read-only and workspace-scoped."""

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import ServiceProvider, org_of
from app.api.insights import PERIOD, checked_period, money
from app.core.auth import Principal
from app.domain.readiness import Check, OpenFinding
from app.services.readiness_service import ReadinessReport


def _rate(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _finding(f: OpenFinding) -> dict[str, Any]:
    return {
        "findingId": f.finding_id,
        "code": f.code,
        "severity": f.severity,
        "title": f.title,
        "month": f.month,
        "nextStep": f.next_step,
        "link": f"/risk/{f.finding_id}",
    }


def _check(c: Check) -> dict[str, Any]:
    return {
        "id": c.id,
        "status": c.status,
        "months": list(c.months),
        "count": c.count,
        "threshold": c.threshold,
        "findings": [_finding(f) for f in c.findings],
    }


def readiness_body(report: ReadinessReport) -> dict[str, Any]:
    r, c = report.readiness, report.currency
    t = r.totals
    return {
        "workspace": report.workspace,
        "currency": c,
        "framework": report.framework,
        "period": report.period,
        "generatedAt": report.generated_at.isoformat(),
        "level": r.level,
        "checks": [_check(check) for check in r.checks],
        "totals": {
            "months": t.months,
            "moneyIn": money(t.money_in, c),
            "moneyOut": money(t.money_out, c),
            "net": money(t.net, c),
            "averageIn": money(t.average_in, c),
            "averageOut": money(t.average_out, c),
            "averageNet": money(t.average_net, c),
            "matchedShare": _rate(t.matched_share),
            "closing": money(t.closing, c),
        },
        "months": [
            {
                "month": m.month,
                "statementsPresent": m.statements_present,
                "statementsExpected": m.statements_expected,
                "reconciled": m.reconciled,
                "moneyIn": money(m.money_in, c),
                "moneyOut": money(m.money_out, c),
                "net": money(m.net, c),
                "closing": money(m.closing, c),
                "matchedShare": _rate(m.matched_share),
                "riskLevel": m.risk_level,
                "explanation": m.explanation,
            }
            for m in r.months
        ],
        "clients": [
            {"name": x.name, "moneyIn": money(x.money_in, c), "share": str(x.share)}
            for x in r.clients
        ],
        "documents": [{"type": kind, "count": n} for kind, n in r.documents],
    }


def create_readiness_router(provider: ServiceProvider, workspace_dep: Any) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["readiness"])

    @router.get("/readiness")
    async def get_readiness(
        period: str = Query(default="all", pattern=PERIOD),
        principal: Principal = Depends(workspace_dep),
    ) -> dict[str, Any]:
        report = await provider.readiness_service.report(
            org_of(principal), period=checked_period(period)
        )
        return readiness_body(report)

    return router
