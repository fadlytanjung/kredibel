"""Reading bank lines for the API (docs/10 §2.4): money in the workspace's currency (ADR-020)."""

from dataclasses import replace

from app.core.auth import Principal
from app.core.clock import Clock
from app.core.ids import new_id
from app.domain.categorize import CategoryPolicy, category_fits
from app.domain.errors import NotFoundError, ValidationProblem, WorkspaceRequiredError
from app.domain.models.bank_line import BankLine
from app.domain.models.events import AuditEvent
from app.ports.bank_line_repository import BankLineRepository
from app.ports.workspace_repository import WorkspaceRepository
from app.services.month_service import MonthService


class BankLineService:
    def __init__(
        self,
        *,
        bank_lines: BankLineRepository,
        workspaces: WorkspaceRepository,
        categories: CategoryPolicy,
        clock: Clock,
        months: MonthService,
    ) -> None:
        self._lines = bank_lines
        self._workspaces = workspaces
        self._categories = categories
        self._clock = clock
        self._months = months

    async def set_category(
        self,
        principal: Principal,
        tx_id: str,
        category: str,
    ) -> tuple[BankLine, str]:
        org_id = principal.org_id
        if org_id is None:
            raise WorkspaceRequiredError()
        line = await self._lines.get_line(org_id, tx_id)
        if line is None:
            raise NotFoundError("Bank line not found")
        workspace = await self._workspaces.get_workspace(org_id)
        if workspace is None:
            raise WorkspaceRequiredError()
        chosen = self._categories.categories.get(category)
        if chosen is None or not category_fits(chosen, line.amount):
            raise ValidationProblem("category", "Choose a category for this line's direction.")
        framework = workspace.profile.accounting_framework
        changed = replace(
            line,
            category=category,
            categorized_by="USER",
            category_confidence=None,
            cashflow_class=chosen.cashflow_class("US_GAAP" if framework == "US_GAAP" else "IFRS"),
        )
        event = AuditEvent(
            event_id=new_id("evt"),
            type="CATEGORY_CHANGED",
            actor_uid=principal.uid,
            actor_role=principal.role or "owner",
            at=self._clock.now(),
            subject={"txId": tx_id, "docId": line.doc_id},
            details={"before": line.category, "after": category},
        )
        await self._lines.set_category(org_id, changed, event)
        await self._months.mark_dirty(org_id, [line.month])
        return changed, workspace.currency

    async def rederive_cashflow(self, org_id: str, framework: str) -> list[str]:
        """AC-016-8: the framework changed, so every line's cash-flow class is derived again from
        categories.v1.yaml; categories stay as they are; every month with lines runs once."""
        chosen = "US_GAAP" if framework == "US_GAAP" else "IFRS"
        lines = await self._lines.list_lines(org_id, limit=100_000)
        updates = {}
        for line in lines:
            category = self._categories.categories.get(line.category)
            if category is None:
                continue
            cashflow = category.cashflow_class(chosen)
            if cashflow != line.cashflow_class:
                updates[line.tx_id] = cashflow
        if updates:
            await self._lines.set_cashflow_classes(org_id, updates)
        months = sorted({line.month for line in lines})
        if months:
            await self._months.mark_dirty(org_id, months, reason="framework_changed")
        return months

    async def list_lines(
        self,
        org_id: str,
        *,
        doc_id: str | None,
        month: str | None,
        limit: int,
        counterparty_id: str | None = None,
    ) -> tuple[list[BankLine], str]:
        workspace = await self._workspaces.get_workspace(org_id)
        currency = workspace.currency if workspace else "IDR"
        return await self._lines.list_lines(
            org_id, doc_id=doc_id, month=month, counterparty_id=counterparty_id, limit=limit
        ), currency
