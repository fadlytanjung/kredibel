"""A WorkspaceCopier that records what it was asked to copy (spec 021); it can be told to fail."""

from typing import Any

from app.ports.workspace_copier import WorkspaceCopier


class FakeWorkspaceCopier(WorkspaceCopier):
    def __init__(self, records: int = 1284, fail: bool = False, workspaces: Any = None) -> None:
        self.records = records
        self.fail = fail
        self.workspaces = workspaces  # a FakeWorkspaceRepository: discard removes the workspace
        self.copies: list[tuple[str, str, dict[str, str]]] = []
        self.fields: list[tuple[str, str]] = []
        self.discarded: list[str] = []

    async def copy_records(self, source_org: str, target_org: str, replace: dict[str, str]) -> int:
        self.copies.append((source_org, target_org, dict(replace)))
        if self.fail:
            raise RuntimeError("the copy broke half way")
        return self.records

    async def copy_workspace_fields(
        self, source_org: str, target_org: str, replace: dict[str, str]
    ) -> None:
        self.fields.append((source_org, target_org))

    async def discard(self, org_id: str) -> None:
        self.discarded.append(org_id)
        if self.workspaces is not None:
            self.workspaces.workspaces.pop(org_id, None)
            self.workspaces.members.pop(org_id, None)
