"""One reporting path for dashboard and assistant (spec 018). Accrual from the ledger export when
the workspace has one; otherwise cash basis from its categorized bank lines (ADR-027 amendment)."""

import asyncio
from hashlib import sha256
from typing import Any

from app.core.clock import Clock
from app.core.ids import new_id
from app.domain.categorize import CategoryPolicy
from app.domain.errors import ForbiddenError, ValidationProblem, WorkspaceRequiredError
from app.domain.models.document import DocStatus, DocType, DuplicateKind
from app.domain.models.events import AuditEvent
from app.domain.profit_loss import (
    Classification,
    ProfitLoss,
    ProfitLossPolicy,
    build_cash_profit_loss,
    build_profit_loss,
)
from app.ports.bank_line_repository import BankLineRepository
from app.ports.document_repository import DocumentRepository
from app.ports.ledger_repository import LedgerRepository
from app.ports.workspace_repository import WorkspaceRepository


class ProfitLossService:
    def __init__(
        self,
        *,
        ledger: LedgerRepository,
        workspaces: WorkspaceRepository,
        documents: DocumentRepository,
        policy: ProfitLossPolicy,
        clock: Clock,
        bank_lines: BankLineRepository | None = None,
        categories: CategoryPolicy | None = None,
    ):
        self._ledger = ledger
        self._workspaces = workspaces
        self._documents = documents
        self._policy = policy
        self._clock = clock
        self._bank_lines = bank_lines
        self._categories = categories

    async def report(self, org_id: str, period: str = "recent") -> ProfitLoss:
        workspace = await self._workspaces.get_workspace(org_id)
        if workspace is None:
            raise WorkspaceRequiredError()
        rows = await self._ledger.list_rows(org_id)
        if not rows and self._bank_lines is not None and self._categories is not None:
            return await self._cash_report(org_id, workspace.currency, period)
        mappings = await self._ledger.classifications(org_id)
        ids = sorted({r.doc_id for r in rows})
        docs = await asyncio.gather(*(self._documents.get_document(org_id, d) for d in ids))
        excluded = {}
        for doc_id, doc in zip(ids, docs, strict=True):
            if doc is None or doc.doc_type != DocType.LEDGER_EXPORT or doc.status != DocStatus.DONE:
                excluded[doc_id] = "SOURCE_UNAVAILABLE"
            elif doc.held_as_duplicate or (
                doc.duplicate and doc.duplicate.kind == DuplicateKind.EXACT
            ):
                excluded[doc_id] = "HELD_DUPLICATE"
        try:
            return build_profit_loss(
                rows,
                mappings,
                self._policy,
                currency=workspace.currency,
                period=period,
                excluded_docs=excluded,
            )
        except ValueError as exc:
            raise ValidationProblem(
                "period", "Select a valid chronological reporting period."
            ) from exc

    async def _cash_report(self, org_id: str, currency: str, period: str) -> ProfitLoss:
        assert self._bank_lines is not None and self._categories is not None
        lines = await self._bank_lines.list_lines(org_id, limit=5000)
        ids = sorted({line.doc_id for line in lines})
        docs = await asyncio.gather(*(self._documents.get_document(org_id, d) for d in ids))
        excluded = {}
        for doc_id, doc in zip(ids, docs, strict=True):
            if doc is None:
                excluded[doc_id] = "SOURCE_UNAVAILABLE"
            elif doc.held_as_duplicate or (
                doc.duplicate and doc.duplicate.kind == DuplicateKind.EXACT
            ):
                excluded[doc_id] = "HELD_DUPLICATE"
        try:
            return build_cash_profit_loss(
                lines,
                self._categories,
                self._policy,
                currency=currency,
                period=period,
                excluded_docs=excluded,
            )
        except ValueError as exc:
            raise ValidationProblem(
                "period", "Select a valid chronological reporting period."
            ) from exc

    async def accounts(self, org_id: str) -> dict[str, Any]:
        mappings = await self._ledger.classifications(org_id)
        rows = await self._ledger.list_rows(org_id)
        if not rows and self._categories is not None:
            # No ledger export: the category labels of the policy stand in, read-only.
            return {
                "basis": "CASH",
                "accounts": [
                    {
                        "accountCode": c.id,
                        "accountName": c.label,
                        "classification": {
                            "accountCode": c.id,
                            "pnlLine": c.pnl_line,
                            "subledger": c.subledger,
                        },
                    }
                    for c in self._categories.categories.values()
                    if c.pnl_line and c.subledger
                ],
                "pnlLines": {key: value.label for key, value in self._policy.lines.items()},
                "subledgers": self._policy.subledgers,
            }
        accounts = {r.account_code: r.account_name for r in sorted(rows, key=lambda r: r.entry_id)}
        return {
            "basis": "ACCRUAL",
            "accounts": [
                {
                    "accountCode": code,
                    "accountName": name,
                    "classification": mappings[code].model_dump(by_alias=True)
                    if code in mappings
                    else None,
                }
                for code, name in sorted(accounts.items())
            ],
            "pnlLines": {key: value.label for key, value in self._policy.lines.items()},
            "subledgers": self._policy.subledgers,
        }

    async def confirm(
        self, org_id: str, uid: str, role: str | None, classification: Classification
    ) -> Classification:
        if role not in ("owner", "accountant"):
            raise ForbiddenError("Only owners and accountants can classify accounts.")
        if classification.pnl_line not in self._policy.lines:
            raise ValidationProblem("pnlLine", "Choose a P&L line from the catalog.")
        if classification.subledger not in self._policy.subledgers:
            raise ValidationProblem("subledger", "Choose a subledger from the catalog.")
        rows = await self._ledger.list_rows(org_id)
        if classification.account_code not in {r.account_code for r in rows}:
            raise ValidationProblem("accountCode", "Choose an imported account in this workspace.")
        event = AuditEvent(
            event_id=new_id("evt"),
            type="ACCOUNT_CLASSIFIED",
            actor_uid=uid,
            actor_role=role,
            at=self._clock.now(),
            subject={"accountId": sha256(classification.account_code.encode()).hexdigest()},
            details={"pnlLine": classification.pnl_line, "subledger": classification.subledger},
        )
        await self._ledger.confirm(org_id, classification, event)
        return classification
