"""In-memory fake run repository for tests."""

from datetime import UTC, datetime

from app.domain.models.run import Run, RunKind, RunStage, RunStatus
from app.ports.run_repository import RunRepository


class FakeRunRepository(RunRepository):
    def __init__(self) -> None:
        self.runs: dict[tuple[str, str], Run] = {}

    async def create(self, org_id: str, run: Run) -> None:
        self.runs[(org_id, run.run_id)] = run

    async def get(self, org_id: str, run_id: str) -> Run | None:
        return self.runs.get((org_id, run_id))

    async def update_status(
        self, org_id: str, run_id: str, status: RunStatus, ended: bool = False
    ) -> None:
        run = self.runs.get((org_id, run_id))
        if run:
            run.status = status
            if ended:
                run.ended_at = datetime.now(UTC)

    async def append_stage(self, org_id: str, run_id: str, stage: RunStage) -> None:
        run = self.runs.get((org_id, run_id))
        if run:
            run.stages.append(stage)

    async def set_trace_id(self, org_id: str, run_id: str, trace_id: str) -> None:
        run = self.runs.get((org_id, run_id))
        if run:
            run.trace_id = trace_id

    async def list_by_target(self, org_id: str, target: str) -> list[Run]:
        return [r for (o, _), r in self.runs.items() if o == org_id and r.target == target]

    async def list_runs(
        self,
        org_id: str,
        *,
        kind: RunKind | None = None,
        target: str | None = None,
        status: RunStatus | None = None,
        limit: int = 50,
    ) -> list[Run]:
        res = [r for (o, _), r in self.runs.items() if o == org_id]
        if target is not None:
            res = [r for r in res if r.target == target]
        if kind is not None:
            res = [r for r in res if r.kind == kind]
        if status is not None:
            res = [r for r in res if r.status == status]
        res.sort(
            key=lambda r: r.created_at or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        return res[:limit]
