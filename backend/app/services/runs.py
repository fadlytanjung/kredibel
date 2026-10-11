"""Run service for coordinating workflow executions (spec 004).

Normative references:
- spec 004 US-004-1 (AC-004-1, AC-004-3)
- spec 004 US-004-2 (AC-004-4, AC-004-5, AC-004-6)
- spec 004 US-004-4 (AC-004-10, AC-004-11)
- ADR-006 (Async jobs with Cloud Tasks)
"""

from datetime import UTC, datetime
from typing import Any

from app.core.settings import Settings
from app.domain.errors import RunQuotaExceededError, RunsDisabledError
from app.domain.models.run import Run, RunKind, RunStatus
from app.ports.month_repository import MonthRepository
from app.ports.run_repository import RunRepository
from app.ports.task_queue import TaskQueue
from app.services.entitlement_service import EntitlementService, _seconds_until_utc_midnight


class RunService:
    def __init__(
        self,
        *,
        run_repo: RunRepository,
        month_repo: MonthRepository,
        task_queue: TaskQueue,
        entitlement_service: EntitlementService,
        settings: Settings,
        clock: Any | None = None,
    ) -> None:
        self._run_repo = run_repo
        self._month_repo = month_repo
        self._task_queue = task_queue
        self._entitlement_service = entitlement_service
        self._settings = settings
        self._clock = clock

    def _now(self) -> datetime:
        if self._clock is not None:
            return self._clock.now()
        return datetime.now(UTC)

    async def start_document_run(self, org_id: str, doc_id: str, attempt: int = 1) -> Run:
        """Create and enqueue doc-{docId}-{attempt} task (AC-004-1, AC-004-10)."""
        if not self._settings.runs_enabled:
            raise RunsDisabledError()

        run_id = f"doc-{doc_id}-{attempt}"
        run = Run(
            run_id=run_id,
            kind=RunKind.DOCUMENT,
            target=doc_id,
            status=RunStatus.QUEUED,
            created_at=self._now(),
        )
        await self._run_repo.create(org_id, run)
        await self._task_queue.enqueue_document_task(org_id, doc_id, run_id, attempt=attempt)
        return run

    async def start_month_run(
        self, org_id: str, month: str, *, is_user_request: bool = False
    ) -> Run:
        """Mark dirty, bump generation, and enqueue month-{orgId}-{yyyy-mm}-{gen}.

        Normative references: AC-004-4, AC-004-11.
        """
        if not self._settings.runs_enabled:
            raise RunsDisabledError()

        delay_seconds = self._settings.month_run_delay_seconds
        paused_note: str | None = None

        now = self._now()
        if is_user_request:
            # User-requested run: must pass quota check, otherwise 429 RUN_QUOTA_EXCEEDED
            await self._entitlement_service.reserve_month_run(org_id)
        else:
            # Automatic run: never dropped. Past limit, delayed until tomorrow (AC-004-11).
            try:
                await self._entitlement_service.reserve_month_run(org_id)
            except RunQuotaExceededError:
                delay_seconds = _seconds_until_utc_midnight(now) + 60
                paused_note = "Reconciliation paused until tomorrow (daily limit)"

        # Bump generation and mark dirty in transaction
        generation, month_doc = await self._month_repo.bump_generation(org_id, month, dirty=True)
        if paused_note:
            month_doc.note = paused_note
            await self._month_repo.save(org_id, month_doc)

        task_name = f"month-{org_id}-{month}-{generation}"
        run = Run(
            run_id=task_name,
            kind=RunKind.MONTH,
            target=month,
            generation=generation,
            status=RunStatus.QUEUED,
            created_at=now,
        )
        await self._run_repo.create(org_id, run)
        await self._task_queue.enqueue_month_task(
            org_id, month, generation, delay_seconds=delay_seconds
        )
        return run
