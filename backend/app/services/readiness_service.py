"""The loan readiness report of a period (spec 025, ADR-028): the inputs gathered from what the
month runs stored and the dashboard computes, the report from domain/readiness.py. Read-only."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.clock import Clock
from app.domain.errors import WorkspaceRequiredError
from app.domain.models.document import DocStatus, DuplicateKind
from app.domain.models.month import Month, MonthState
from app.domain.readiness import (
    GapFact,
    MonthFacts,
    OpenFinding,
    Readiness,
    ReadinessInput,
    ReadinessPolicy,
    assess_readiness,
)
from app.ports.document_repository import DocumentRepository
from app.ports.finding_repository import FindingRepository
from app.ports.month_repository import MonthRepository
from app.ports.review_item_repository import ReviewItemRepository
from app.ports.workspace_repository import WorkspaceRepository
from app.services.insight_service import InsightService

READY = {MonthState.RECONCILED, MonthState.NEEDS_REVIEW, MonthState.SIGNED_OFF}
CLIENT = "src:client:"


@dataclass(frozen=True)
class ReadinessReport:
    workspace: str
    currency: str
    framework: str
    period: str
    generated_at: datetime
    readiness: Readiness


def _number(figures: dict[str, Any], name: str) -> Decimal | None:
    raw = figures.get(name)
    value = raw.get("value") if isinstance(raw, dict) else raw
    try:
        return None if value is None else Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _count(figures: dict[str, Any], name: str) -> int:
    value = _number(figures, name)
    return int(value) if value is not None else 0


def _explanation(month: Month | None) -> str | None:
    """The month run's risk explanation, only when the grounding guard verified it (spec 008)."""
    risk = (month.risk if month else None) or {}
    summary = risk.get("summary")
    return summary if risk.get("grounding") == "VERIFIED" and isinstance(summary, str) else None


class ReadinessService:
    def __init__(
        self,
        *,
        insights: InsightService,
        workspaces: WorkspaceRepository,
        months: MonthRepository,
        findings: FindingRepository,
        review_items: ReviewItemRepository,
        documents: DocumentRepository,
        policy: ReadinessPolicy,
        clock: Clock,
    ) -> None:
        self._insights = insights
        self._workspaces = workspaces
        self._months = months
        self._findings = findings
        self._review_items = review_items
        self._documents = documents
        self._policy = policy
        self._clock = clock

    async def report(self, org_id: str, *, period: str = "all") -> ReadinessReport:
        workspace = await self._workspaces.get_workspace(org_id)
        if workspace is None:
            raise WorkspaceRequiredError()
        cash, currency, resolved = await self._insights.cash_flow(org_id, period=period)
        cap = self._policy.max_months
        if len(resolved.months) > cap:  # the latest months the policy allows
            last = resolved.months[-cap:]
            period = f"{last[0]}..{last[-1]}"
            cash, currency, resolved = await self._insights.cash_flow(org_id, period=period)

        strip = {chip.month: chip for chip in await self._insights.month_strip(org_id)}
        stored = {m.month: m for m in await self._months.list(org_id)}
        closing = {m.month: m.closing for m in cash.months}
        months: list[MonthFacts] = []
        for cm in cash.months:
            chip = strip.get(cm.month)
            if chip is None or chip.statements_present == 0:
                continue  # no read statement this month: nothing to show a lender
            doc = stored.get(cm.month)
            figures = (doc.figures if doc else None) or {}
            months.append(
                MonthFacts(
                    month=cm.month,
                    statements_present=chip.statements_present,
                    statements_expected=chip.statements_expected,
                    reconciled=doc is not None and doc.state in READY and not doc.dirty,
                    auto_matched=_count(figures, "autoMatched"),
                    in_scope=_count(figures, "bankLines") - _count(figures, "excluded"),
                    money_in=cm.money_in,
                    money_out=cm.money_out,
                    closing=closing.get(cm.month),
                    negative_days=_count(figures, "negativeDays"),
                    risk_level=chip.risk_level,
                    explanation=_explanation(doc),
                )
            )
        in_period = {m.month for m in months}

        findings = await self._findings.list_findings(org_id, status="OPEN", limit=500)
        queue, _, _ = await self._review_items.list_review_items(org_id, status="OPEN", limit=500)
        flow, _, _ = await self._insights.money_flow(
            org_id, period=resolved.key, view="COUNTERPARTIES"
        )
        docs, _ = await self._documents.list_documents(org_id, limit=500)
        read: dict[str, int] = {}
        for d in docs:
            exact = d.duplicate is not None and d.duplicate.kind == DuplicateKind.EXACT
            if d.status != DocStatus.DONE or exact or d.held_as_duplicate:
                continue
            if d.months and not in_period.intersection(d.months):
                continue
            kind = str(d.doc_type.value if d.doc_type else "UNKNOWN")
            read[kind] = read.get(kind, 0) + 1

        data = ReadinessInput(
            months=tuple(months),
            gaps=tuple(GapFact(g.kind, g.month, g.account) for g in cash.gaps),
            findings=tuple(
                OpenFinding(
                    finding_id=f.finding_id,
                    code=f.code,
                    severity=f.severity,
                    title=f.title,
                    month=f.month,
                    next_step=f.next_steps[0] if f.next_steps else None,
                )
                for f in findings
            ),
            open_review_items=len(queue),
            money_in_by_client=tuple(
                (n.label, n.value) for n in flow.nodes if n.id.startswith(CLIENT)
            ),
            documents=tuple(read.items()),
        )
        framework = "US_GAAP" if workspace.profile.accounting_framework == "US_GAAP" else "IFRS"
        return ReadinessReport(
            workspace=workspace.profile.legal_name or workspace.name,
            currency=currency,
            framework=framework,
            period=resolved.key,
            generated_at=self._clock.now(),
            readiness=assess_readiness(data, self._policy),
        )
