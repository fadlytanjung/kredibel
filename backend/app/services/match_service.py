"""Manual matching and unmatching (spec 007, T007-09, AC-007-13).

A person's manual match is confirmed, audited, and preserved across re-runs.
Unmatching marks the match REJECTED so it is never proposed again, and reruns the month.
"""

from collections.abc import Sequence
from dataclasses import replace
from decimal import Decimal

from app.core.auth import Principal
from app.core.clock import Clock
from app.core.ids import new_id
from app.domain.errors import (
    AlreadyMatchedError,
    NotFoundError,
    ToleranceExceededError,
    ValidationProblem,
    WorkspaceRequiredError,
)
from app.domain.models.events import AuditEvent
from app.domain.models.invoice import Invoice, Receipt
from app.domain.models.match import MatchKind, StoredMatch
from app.domain.reconcile import match_key
from app.domain.reconciliation_policy import ReconciliationPolicy
from app.ports.bank_line_repository import BankLineRepository
from app.ports.match_repository import MatchRepository
from app.ports.month_repository import MonthRepository
from app.ports.record_repository import DocumentRecords
from app.ports.task_queue import TaskQueue
from app.ports.workspace_repository import WorkspaceRepository


class MatchService:
    def __init__(
        self,
        *,
        matches: MatchRepository,
        bank_lines: BankLineRepository,
        invoices: DocumentRecords[Invoice],
        receipts: DocumentRecords[Receipt],
        workspaces: WorkspaceRepository,
        month_repo: MonthRepository,
        task_queue: TaskQueue,
        reconciliation: ReconciliationPolicy,
        clock: Clock,
        month_run_delay_seconds: int,
    ) -> None:
        self._matches = matches
        self._bank_lines = bank_lines
        self._invoices = invoices
        self._receipts = receipts
        self._workspaces = workspaces
        self._months = month_repo
        self._queue = task_queue
        self._policy = reconciliation
        self._clock = clock
        self._delay = month_run_delay_seconds

    async def create_manual_match(
        self,
        principal: Principal,
        *,
        bank_line_ids: list[str],
        invoice_ids: list[str] | None = None,
        receipt_ids: list[str] | None = None,
        ledger_entry_ids: list[str] | None = None,
        note: str | None = None,
    ) -> StoredMatch:
        org_id = _org(principal)
        inv_ids = invoice_ids or []
        rc_ids = receipt_ids or []
        doc_count = len(inv_ids) + len(rc_ids) + len(ledger_entry_ids or [])

        if not (1 <= len(bank_line_ids) <= 3):
            raise ValidationProblem("bankLineIds", "Choose between 1 and 3 bank lines.")
        if not (1 <= doc_count <= 5):
            raise ValidationProblem("documents", "Choose between 1 and 5 supporting records.")

        # Load and verify bank lines
        lines = []
        for tx_id in bank_line_ids:
            line = await self._bank_lines.get_line(org_id, tx_id)
            if line is None:
                raise NotFoundError(f"Bank line {tx_id} not found")
            lines.append(line)

        # Determine month from bank lines (they must share the month)
        months = {line.month for line in lines}
        if len(months) > 1:
            raise ValidationProblem("bankLineIds", "All bank lines must belong to the same month.")
        month = lines[0].month

        # Load invoices
        invoices = []
        for inv_id in inv_ids:
            inv = await self._invoices.get_record(org_id, inv_id)
            if inv is None:
                raise NotFoundError(f"Invoice {inv_id} not found")
            invoices.append(inv)

        # Load receipts
        receipts = []
        for rc_id in rc_ids:
            rc = await self._receipts.get_record(org_id, rc_id)
            if rc is None:
                raise NotFoundError(f"Receipt {rc_id} not found")
            receipts.append(rc)

        # Check existing confirmed matches to avoid double-matching
        existing_matches = await self._matches.list_matches(org_id, month=month, status="CONFIRMED")
        for em in existing_matches:
            for tx_id in bank_line_ids:
                if tx_id in em.bank_line_ids:
                    raise AlreadyMatchedError(tx_id, em.match_id)
            for inv_id in inv_ids:
                if inv_id in em.invoice_ids:
                    raise AlreadyMatchedError(inv_id, em.match_id)
            for rc_id in rc_ids:
                if rc_id in em.receipt_ids:
                    raise AlreadyMatchedError(rc_id, em.match_id)

        # Compute amounts and check tolerance
        workspace = await self._workspaces.get_workspace(org_id)
        currency = workspace.currency if workspace else "IDR"

        bank_total = sum((abs(line.amount) for line in lines), Decimal("0"))
        doc_total = sum((inv.total or Decimal("0") for inv in invoices), Decimal("0")) + sum(
            (rc.total or Decimal("0") for rc in receipts), Decimal("0")
        )
        diff = abs(bank_total - doc_total)

        max_tol = self._policy.tolerance(bank_total, currency)
        if max_tol is not None and diff > max_tol:
            raise ToleranceExceededError(diff, max_tol)

        # Determine match kind
        if receipts:
            kind: MatchKind = "BANK_RECEIPT"
        elif invoices and all(inv.kind == "SALES" for inv in invoices):
            kind = "BANK_SALES_INVOICE"
        else:
            kind = "BANK_PURCHASE_INVOICE"

        match_id = match_key(bank_line_ids, [*inv_ids, *rc_ids])
        reasons = ["MANUAL_MATCH"]
        if note:
            reasons.append(note)

        now = self._clock.now()
        match = StoredMatch(
            match_id=match_id,
            month=month,
            kind=kind,
            status="CONFIRMED",
            method="MANUAL",
            bank_line_ids=bank_line_ids,
            invoice_ids=inv_ids,
            receipt_ids=rc_ids,
            amount=bank_total,
            amount_difference=diff,
            score=Decimal("1.0"),
            reasons=reasons,
            created_by=principal.uid,
            created_at=now,
        )

        details: dict[str, str | int | bool] = {
            "method": "MANUAL",
            "bankLines": ",".join(bank_line_ids),
            "invoices": ",".join(inv_ids),
            "receipts": ",".join(rc_ids),
        }
        if note:
            details["note"] = note

        event = AuditEvent(
            event_id=new_id("evt"),
            type="MATCH_CREATED",
            actor_uid=principal.uid,
            actor_role=principal.role or "owner",
            at=now,
            subject={"matchId": match_id, "month": month},
            details=details,
        )

        await self._matches.save(org_id, match, event)
        await self._rerun(org_id, [month])
        return match

    async def unmatch(self, principal: Principal, match_id: str) -> None:
        org_id = _org(principal)
        match = await self._matches.get(org_id, match_id)
        if match is None:
            raise NotFoundError(f"Match {match_id} not found")

        if match.status == "REJECTED":
            return

        now = self._clock.now()
        rejected = replace(match, status="REJECTED", method="MANUAL")
        event = AuditEvent(
            event_id=new_id("evt"),
            type="MATCH_REJECTED",
            actor_uid=principal.uid,
            actor_role=principal.role or "owner",
            at=now,
            subject={"matchId": match_id, "month": match.month},
            details={"previousStatus": match.status, "previousMethod": match.method or "NONE"},
        )

        await self._matches.save(org_id, rejected, event)
        await self._rerun(org_id, [match.month])

    async def _rerun(self, org_id: str, months: Sequence[str]) -> None:
        for month in months:
            generation, _ = await self._months.bump_generation(org_id, month, dirty=True)
            await self._queue.enqueue_month_task(
                org_id, month, generation, delay_seconds=self._delay
            )


def _org(principal: Principal) -> str:
    if principal.org_id is None:
        raise WorkspaceRequiredError()
    return principal.org_id
