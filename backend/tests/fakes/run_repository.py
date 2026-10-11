"""In-memory fake run repository for tests."""

from datetime import UTC, datetime

from app.domain.models.run import Run, RunStage, RunStatus
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

    async def list_by_target(self, org_id: str, target: str) -> list[Run]:
        return [r for (o, _), r in self.runs.items() if o == org_id and r.target == target]
