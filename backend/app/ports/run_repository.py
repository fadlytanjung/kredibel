"""Run repository port interface (docs/09 §3.15)."""

from typing import Protocol

from app.domain.models.run import Run, RunStage, RunStatus


class RunRepository(Protocol):
    """Port for persisting and managing workflow runs and stages."""

    async def create(self, org_id: str, run: Run) -> None:
        """Create a new run record."""
        ...

    async def get(self, org_id: str, run_id: str) -> Run | None:
        """Get a run by ID."""
        ...

    async def update_status(
        self, org_id: str, run_id: str, status: RunStatus, ended: bool = False
    ) -> None:
        """Update run status."""
        ...

    async def append_stage(self, org_id: str, run_id: str, stage: RunStage) -> None:
        """Append a stage record to the run."""
        ...

    async def list_by_target(self, org_id: str, target: str) -> list[Run]:
        """List runs for a specific target (docId or yyyy-mm)."""
        ...
