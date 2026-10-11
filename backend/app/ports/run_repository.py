"""Run repository port interface (docs/09 §3.15)."""

from typing import Protocol

from app.domain.models.run import Run, RunKind, RunStage, RunStatus


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

    async def set_trace_id(self, org_id: str, run_id: str, trace_id: str) -> None:
        """Record the Cloud Trace ID of the run's `workflow:` span (docs/17 §2)."""
        ...

    async def list_by_target(self, org_id: str, target: str) -> list[Run]:
        """List runs for a specific target (docId or yyyy-mm)."""
        ...

    async def list_runs(
        self,
        org_id: str,
        *,
        kind: RunKind | None = None,
        target: str | None = None,
        status: RunStatus | None = None,
        limit: int = 50,
    ) -> list[Run]:
        """List runs with optional filters, newest first."""
        ...
