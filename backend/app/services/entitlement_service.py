"""Plan entitlements enforced on the server (spec 013 AC-013-7…10, ADR-011, non-negotiable 12).

Every check runs inside the repository transaction that also moves the counter, so two requests
at the limit cannot both pass (AC-013-9). Usage months and days are UTC.
"""

from datetime import datetime, timedelta

from app.core.clock import Clock
from app.core.errors import (
    DocumentTooLargeError,
    PlanLimitReachedError,
    RunQuotaExceededError,
    TooManyPagesError,
    TooManyRowsError,
    TrialExpiredError,
)
from app.domain.models.workspace import Subscription, UsageDay, UsageMonth
from app.domain.plans import (
    Decision,
    Denied,
    Limits,
    PlanCatalog,
    UploadRequest,
    check_assistant_question,
    check_month_run,
    check_upload,
    effective_limits,
    subscription_status,
)
from app.ports.workspace_repository import (
    PendingWrite,
    UsageIncrement,
    UsageRepository,
    UsageSettlement,
)


def _seconds_until_utc_midnight(now: datetime) -> int:
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return int((midnight - now).total_seconds())


class EntitlementService:
    def __init__(
        self,
        *,
        repo: UsageRepository,
        plans: PlanCatalog,
        clock: Clock,
        run_quota_per_org_per_day: int,
    ) -> None:
        self._repo = repo
        self._plans = plans
        self._clock = clock
        self._run_quota = run_quota_per_org_per_day

    def limits_for(self, subscription: Subscription) -> Limits:
        return effective_limits(
            self._plans.plan(subscription.plan_id), subscription.limit_overrides
        )

    async def reserve_upload(
        self, org_id: str, upload: UploadRequest, writes: tuple[PendingWrite, ...] = ()
    ) -> None:
        """Check and count an upload; `writes` (the document record) commit with the counters."""
        now = self._clock.now()

        def decide(sub: Subscription, month: UsageMonth, _day: UsageDay) -> Decision:
            status = subscription_status(sub, now)
            return check_upload(self.limits_for(sub), status, month, upload)

        increment = (
            UsageIncrement()
            if upload.exact_duplicate
            else UsageIncrement(documents_uploaded=1, pages_reserved=upload.pages_to_read)
        )
        decision, sub = await self._repo.meter(
            org_id,
            month=_month(now),
            day=_day(now),
            decide=decide,
            increment=increment,
            writes=writes,
        )
        if isinstance(decision, Denied):
            raise _error_for(decision, sub)

    async def check_upload_preflight(self, org_id: str, size_bytes: int) -> None:
        """Preflight check for trial status, document limit, and file size before rendering."""
        now = self._clock.now()
        upload = UploadRequest(size_bytes=size_bytes, pages=0, pages_to_read=0)

        def decide(sub: Subscription, month: UsageMonth, _day: UsageDay) -> Decision:
            status = subscription_status(sub, now)
            return check_upload(self.limits_for(sub), status, month, upload)

        decision, sub = await self._repo.meter(
            org_id,
            month=_month(now),
            day=_day(now),
            decide=decide,
            increment=UsageIncrement(),
        )
        if isinstance(decision, Denied):
            raise _error_for(decision, sub)

    async def reserve_month_run(self, org_id: str) -> None:
        """A month run the user asked for (AC-004-11). Automatic runs (spec 004) are counted
        but never refused."""
        now = self._clock.now()

        def decide(sub: Subscription, _month: UsageMonth, day: UsageDay) -> Decision:
            return check_month_run(
                self.limits_for(sub),
                subscription_status(sub, now),
                day,
                global_quota=self._run_quota,
                seconds_until_reset=_seconds_until_utc_midnight(now),
            )

        decision, sub = await self._repo.meter(
            org_id,
            month=_month(now),
            day=_day(now),
            decide=decide,
            increment=UsageIncrement(month_runs=1),
        )
        if isinstance(decision, Denied):
            raise _error_for(decision, sub)

    async def reserve_assistant_question(self, org_id: str) -> None:
        now = self._clock.now()

        def decide(sub: Subscription, _month: UsageMonth, day: UsageDay) -> Decision:
            return check_assistant_question(
                self.limits_for(sub), subscription_status(sub, now), day
            )

        decision, sub = await self._repo.meter(
            org_id,
            month=_month(now),
            day=_day(now),
            decide=decide,
            increment=UsageIncrement(assistant_questions=1),
        )
        if isinstance(decision, Denied):
            raise _error_for(decision, sub)

    async def settle_document_run(self, org_id: str, settlement: UsageSettlement) -> None:
        await self._repo.settle(org_id, settlement)

    async def usage(self, org_id: str) -> tuple[UsageMonth, UsageDay]:
        now = self._clock.now()
        return await self._repo.get_usage(org_id, month=_month(now), day=_day(now))


def _month(now: datetime) -> str:
    return now.strftime("%Y-%m")


def _day(now: datetime) -> str:
    return now.strftime("%Y-%m-%d")


def _error_for(denied: Denied, sub: Subscription) -> Exception:
    match denied.code:
        case "TRIAL_EXPIRED":
            return TrialExpiredError(sub.trial_ends_at)
        case "DOCUMENT_TOO_LARGE":
            return DocumentTooLargeError(denied.limit, denied.used, denied.max)
        case "TOO_MANY_PAGES":
            return TooManyPagesError(denied.used, denied.max)
        case "TOO_MANY_ROWS":
            return TooManyRowsError(denied.limit, denied.used, denied.max)
        case "RUN_QUOTA_EXCEEDED":
            return RunQuotaExceededError(denied.used, denied.max, denied.retry_after_seconds or 0)
        case "PLAN_LIMIT_REACHED":
            return PlanLimitReachedError(denied.limit, denied.used, denied.max)
