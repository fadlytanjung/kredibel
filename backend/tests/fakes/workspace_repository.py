"""In-memory WorkspaceRepository; a lock stands in for the Firestore transaction."""

import asyncio

from app.domain.models.events import AuditEvent
from app.domain.models.workspace import BankAccount, Workspace
from app.ports.workspace_repository import (
    AlreadyMember,
    Created,
    CreateOutcome,
    NewWorkspace,
    OwnerMember,
    SignupLimitReached,
    WorkspaceRepository,
)


class FakeWorkspaceRepository(WorkspaceRepository):
    def __init__(self, workspaces_created: int = 0) -> None:
        self.workspaces: dict[str, Workspace] = {}
        self.members: dict[str, dict[str, OwnerMember]] = {}
        self.bank_accounts: dict[str, dict[str, BankAccount]] = {}
        self.account_hashes: dict[str, dict[str, str]] = {}
        self.events: dict[str, list[AuditEvent]] = {}
        self.users: dict[str, AlreadyMember] = {}
        self.workspaces_created = workspaces_created
        self._txn = asyncio.Lock()

    async def create_workspace(self, new: NewWorkspace, *, max_workspaces: int) -> CreateOutcome:
        async with self._txn:
            uid = new.owner.uid
            if uid in self.users:
                return self.users[uid]
            if self.workspaces_created >= max_workspaces:
                return SignupLimitReached(self.workspaces_created)
            # Yield inside the "transaction" so concurrent callers really interleave.
            await asyncio.sleep(0)
            org_id = new.workspace.org_id
            self.workspaces[org_id] = new.workspace
            self.members[org_id] = {uid: new.owner}
            self.bank_accounts[org_id] = {
                b.account.account_id: b.account for b in new.bank_accounts
            }
            self.account_hashes[org_id] = {
                b.account.account_id: b.account_hash for b in new.bank_accounts
            }
            self.events[org_id] = list(new.events)
            self.users[uid] = AlreadyMember(org_id=org_id, role=new.owner.role)
            self.workspaces_created += 1
            return Created(org_id)

    async def get_workspace(self, org_id: str) -> Workspace | None:
        return self.workspaces.get(org_id)

    async def list_bank_accounts(self, org_id: str) -> list[BankAccount]:
        return list(self.bank_accounts.get(org_id, {}).values())
