"""Copy a workspace's records and files into another workspace (spec 021). Server only."""

from typing import Protocol


class WorkspaceCopier(Protocol):
    async def copy_records(self, source_org: str, target_org: str, replace: dict[str, str]) -> int:
        """Every collection under the source workspace (but the skipped ones) and its server-only
        records, and every stored file, rewritten; the number of records written."""
        ...

    async def copy_workspace_fields(
        self, source_org: str, target_org: str, replace: dict[str, str]
    ) -> None:
        """Merge the source record's fields the new workspace does not set itself."""
        ...

    async def discard(self, org_id: str) -> None:
        """Remove what a failed copy wrote: records, server-only records and files."""
        ...
