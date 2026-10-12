"""The dashboard, the money flow and the cash flow of a period (spec 010, T010-02; docs/10 §2.7).

Everything is computed by code from the workspace's read statements: the same eligibility as a
month run (read, not an exact copy, in the workspace currency or agreed by a person), possible
copies held out. A period's flow is rebuilt from its lines, since its five largest clients are not
the sum of each month's.
"""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from app.core.ids import content_id
from app.domain.cash_flow import CashFlow, build_cash_flow
from app.domain.categorize import CategoryPolicy, Framework
from app.domain.errors import WorkspaceRequiredError
from app.domain.models.bank_line import BankLine
from app.domain.models.document import DocStatus, DocType, Document, DuplicateKind
from app.domain.models.month import Month
from app.domain.money_flow import FlowNode, MoneyFlow, View, build_money_flow
from app.domain.period import Period, resolve_period
from app.ports.bank_line_repository import BankLineRepository
from app.ports.decision_repository import DecisionRepository
from app.ports.document_repository import DocumentRepository
from app.ports.finding_repository import FindingRepository
from app.ports.month_repository import MonthRepository
from app.ports.workspace_repository import WorkspaceRepository

ZERO = Decimal("0")
STRIP_MONTHS = 12
ALERT_SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM")


@dataclass(frozen=True)
class Kpi:
    id: str
    kind: Literal["money", "rate", "count"]
    value: Decimal | int
    previous: Decimal | int | None = None


@dataclass(frozen=True)
class MonthChip:
    month: str
    state: str
    statements_present: int
    statements_expected: int
    risk_level: str | None
    auto_match_rate: str | None
    money_in: Decimal | None
    money_out: Decimal | None


@dataclass(frozen=True)
class Alert:
    severity: str
    title: str
    month: str | None
    finding_id: str

    @property
    def link(self) -> str:
        return f"/risk/{self.finding_id}"


@dataclass(frozen=True)
class Dashboard:
    period: Period
    currency: str
    kpis: tuple[Kpi, ...]
    months: tuple[MonthChip, ...]
    alerts: tuple[Alert, ...]
    top_sources: tuple[FlowNode, ...] = field(default_factory=tuple)
    top_uses: tuple[FlowNode, ...] = field(default_factory=tuple)


@dataclass
class _Books:
    currency: str
    framework: Framework
    statements: list[Document]
    account_of: dict[str, str]
    held: frozenset[str]
    months_with_data: list[str]
    month_docs: dict[str, Month]


def account_label(doc: Document) -> str:
    meta = doc.statement_meta or {}
    return " ".join(x for x in (meta.get("bankName"), meta.get("accountMasked")) if x) or doc.doc_id


class InsightService:
    def __init__(
        self,
        *,
        workspaces: WorkspaceRepository,
        doc_repo: DocumentRepository,
        bank_lines: BankLineRepository,
        months: MonthRepository,
        findings: FindingRepository,
        decisions: DecisionRepository,
        categories: CategoryPolicy,
    ) -> None:
        self._workspaces = workspaces
        self._docs = doc_repo
        self._lines = bank_lines
        self._months = months
        self._findings = findings
        self._decisions = decisions
        self._categories = categories

    async def _books(self, org_id: str) -> _Books:
        workspace = await self._workspaces.get_workspace(org_id)
        if workspace is None:
            raise WorkspaceRequiredError()
        docs, _ = await self._docs.list_documents(org_id, limit=500)
        agreed = {
            d.doc_id
            for d in await self._decisions.list_decisions(
                org_id, kind="CURRENCY_AGREEMENT", status="ACTIVE", limit=1000
            )
            if d.doc_id
        }
        statements = [
            d
            for d in docs
            if d.doc_type == DocType.BANK_STATEMENT
            and d.status == DocStatus.DONE
            and not (d.duplicate is not None and d.duplicate.kind == DuplicateKind.EXACT)
            and (
                (d.statement_meta or {}).get("currency") in (None, workspace.currency)
                or d.doc_id in agreed
            )
        ]
        month_docs = {m.month: m for m in await self._months.list(org_id)}
        with_data = {m for d in statements for m in d.months} | {
            m for m, doc in month_docs.items() if doc.figures
        }
        framework: Framework = (
            "US_GAAP" if workspace.profile.accounting_framework == "US_GAAP" else "IFRS"
        )
        return _Books(
            currency=workspace.currency,
            framework=framework,
            statements=statements,
            account_of={d.doc_id: account_label(d) for d in statements},
            held=frozenset(d.doc_id for d in statements if d.held_as_duplicate),
            months_with_data=sorted(with_data),
            month_docs=month_docs,
        )

    async def _lines_of(self, org_id: str, books: _Books, months: Sequence[str]) -> list[BankLine]:
        statements = set(books.account_of)
        found = await asyncio.gather(
            *(self._lines.list_lines(org_id, month=m, limit=5000) for m in sorted(set(months)))
        )
        return [ln for lines in found for ln in lines if ln.doc_id in statements]

    async def money_flow(
        self,
        org_id: str,
        *,
        period: str,
        view: View = "STATEMENT",
        framework: Framework | None = None,
        account_id: str | None = None,
        show_transfers: bool = False,
    ) -> tuple[MoneyFlow, str, Period]:
        books = await self._books(org_id)
        resolved = resolve_period(period, books.months_with_data)
        lines = await self._lines_of(org_id, books, resolved.months)
        if account_id:
            lines = [
                ln
                for ln in lines
                if content_id("acc", books.account_of.get(ln.doc_id, "")) == account_id
            ]
        flow = build_money_flow(
            lines,
            account_of=books.account_of,
            policy=self._categories,
            framework=framework or books.framework,
            view=view,
            show_transfers=show_transfers,
            held_docs=books.held,
        )
        return flow, books.currency, resolved

    async def flow_lines(
        self,
        org_id: str,
        flow_id: str,
        *,
        period: str,
        view: View = "STATEMENT",
        framework: Framework | None = None,
        show_transfers: bool = False,
    ) -> tuple[list[BankLine], str]:
        """The bank lines behind one link, with the flow rebuilt as the chart asked for it."""
        books = await self._books(org_id)
        resolved = resolve_period(period, books.months_with_data)
        lines = await self._lines_of(org_id, books, resolved.months)
        flow = build_money_flow(
            lines,
            account_of=books.account_of,
            policy=self._categories,
            framework=framework or books.framework,
            view=view,
            show_transfers=show_transfers,
            held_docs=books.held,
        )
        wanted = set(flow.lines_of(flow_id))
        return [ln for ln in lines if ln.tx_id in wanted], books.currency

    async def cash_flow(
        self, org_id: str, *, period: str, framework: Framework | None = None
    ) -> tuple[CashFlow, str, Period]:
        books = await self._books(org_id)
        resolved = resolve_period(period, books.months_with_data)
        lines = await self._lines_of(org_id, books, resolved.months)
        return self._cash(books, lines, resolved.months, framework), books.currency, resolved

    def _cash(
        self,
        books: _Books,
        lines: list[BankLine],
        months: Sequence[str],
        framework: Framework | None = None,
    ) -> CashFlow:
        risk = {
            m: str(doc.risk["level"])
            for m, doc in books.month_docs.items()
            if isinstance(doc.risk, dict) and doc.risk.get("level")
        }
        return build_cash_flow(
            lines,
            months=list(months),
            account_of=books.account_of,
            policy=self._categories,
            framework=framework or books.framework,
            risk=risk,
            held_docs=books.held,
        )

    async def dashboard(self, org_id: str, *, period: str = "recent") -> Dashboard:
        books = await self._books(org_id)
        resolved = resolve_period(period, books.months_with_data)
        lines = await self._lines_of(org_id, books, (*resolved.months, *resolved.previous))
        now = [ln for ln in lines if ln.month in resolved.months]
        before = [ln for ln in lines if ln.month in resolved.previous]
        current = self._cash(books, now, resolved.months)
        earlier = self._cash(books, before, resolved.previous) if before else None

        def totals(cash: CashFlow | None) -> tuple[Decimal, Decimal] | None:
            if cash is None:
                return None
            return (
                sum((m.money_in for m in cash.months), ZERO),
                sum((m.money_out for m in cash.months), ZERO),
            )

        this, last = totals(current), totals(earlier)
        assert this is not None
        kpis = [
            Kpi("MONEY_IN", "money", this[0], last[0] if last else None),
            Kpi("MONEY_OUT", "money", this[1], last[1] if last else None),
            Kpi("NET", "money", this[0] - this[1], last[0] - last[1] if last else None),
        ]
        rate = self._auto_match_rate(books, resolved.months)
        if rate is not None:
            kpis.append(
                Kpi(
                    "AUTO_MATCH_RATE", "rate", rate, self._auto_match_rate(books, resolved.previous)
                )
            )
        docs, _ = await self._docs.list_documents(org_id, limit=500)
        waiting = sum(1 for d in docs if d.held_as_duplicate or d.status == DocStatus.NEEDS_INPUT)
        kpis.append(Kpi("DOCUMENTS_WAITING", "count", waiting))

        flow = build_money_flow(
            now,
            account_of=books.account_of,
            policy=self._categories,
            framework=books.framework,
            held_docs=books.held,
        )
        sources = [n for n in flow.nodes if n.column == "SOURCE" and n.id != "src:balance"]
        uses = [n for n in flow.nodes if n.column == "LINE"]

        findings = await self._findings.list_findings(org_id, status="OPEN", limit=50)
        alerts = [
            Alert(f.severity, f.title, f.month, f.finding_id)
            for f in findings
            if f.severity in ALERT_SEVERITIES
        ][:5]
        return Dashboard(
            period=resolved,
            currency=books.currency,
            kpis=tuple(kpis),
            months=tuple(self._strip(books)),
            alerts=tuple(alerts),
            top_sources=tuple(sorted(sources, key=lambda n: (-n.value, n.id))[:3]),
            top_uses=tuple(sorted(uses, key=lambda n: (-n.value, n.id))[:3]),
        )

    @staticmethod
    def _auto_match_rate(books: _Books, months: Sequence[str]) -> Decimal | None:
        matched = in_scope = 0
        for m in months:
            figures = books.month_docs[m].figures if m in books.month_docs else {}

            def value(name: str, figures: dict = figures) -> int:
                fact = figures.get(name) or {}
                return int(fact.get("value") or 0)

            matched += value("autoMatched")
            in_scope += value("bankLines") - value("excluded")
        if in_scope <= 0:
            return None
        return (Decimal(matched) / Decimal(in_scope)).quantize(Decimal("0.0001"))

    def _strip(self, books: _Books) -> list[MonthChip]:
        spans: dict[str, tuple[str, str]] = {}
        covered: dict[str, set[str]] = {}
        for doc in books.statements:
            if not doc.months:
                continue
            account = books.account_of[doc.doc_id]
            first, last = spans.get(account, (min(doc.months), max(doc.months)))
            spans[account] = (min(first, *doc.months), max(last, *doc.months))
            for m in doc.months:
                covered.setdefault(m, set()).add(account)
        chips = []
        for m in books.months_with_data[-STRIP_MONTHS:]:
            doc = books.month_docs.get(m)
            figures = doc.figures if doc else {}

            def money(name: str, figures: dict = figures) -> Decimal | None:
                fact = figures.get(name) or {}
                return Decimal(fact["value"]) if fact.get("value") is not None else None

            expected = sum(1 for first, last in spans.values() if first <= m <= last)
            rate = (figures.get("autoMatchRate") or {}).get("value")
            chips.append(
                MonthChip(
                    month=m,
                    state=str(doc.state.value if doc else "COLLECTING"),
                    statements_present=len(covered.get(m, set())),
                    statements_expected=expected,
                    risk_level=(doc.risk or {}).get("level") if doc else None,
                    auto_match_rate=str(rate) if rate is not None else None,
                    money_in=money("moneyIn"),
                    money_out=money("moneyOut"),
                )
            )
        return chips
