"""In-memory WorkspaceRepository; a lock stands in for the Firestore transaction."""

import asyncio
from datetime import datetime
from typing import Any

from app.domain.models.events import AuditEvent
from app.domain.models.workspace import BankAccount, Workspace
from app.ports.workspace_repository import (
    AlreadyMember,
    Created,
    CreateOutcome,
    NewBankAccount,
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
        self.tours: dict[tuple[str, str], datetime] = {}
        self._txn = asyncio.Lock()

    async def create_workspace(self, new: NewWorkspace, *, max_workspaces: int) -> CreateOutcome:
        async with self._txn:
            uid = new.owner.uid
            if uid in self.users and self.users[uid].org_id in self.workspaces:
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

    async def save_workspace(self, workspace: Workspace, event: AuditEvent) -> None:
        async with self._txn:
            self.workspaces[workspace.org_id] = workspace
            self.events.setdefault(workspace.org_id, []).append(event)

    async def save_ledger_mapping(
        self, org_id: str, layout_signature: str, mapping: dict[str, Any], event: AuditEvent
    ) -> None:
        async with self._txn:
            ws = self.workspaces[org_id]
            self.workspaces[org_id] = ws.model_copy(
                update={"ledger_mappings": {**ws.ledger_mappings, layout_signature: mapping}}
            )
            self.events.setdefault(org_id, []).append(event)

    async def tour_seen(self, org_id: str, uid: str) -> bool:
        return (org_id, uid) in self.tours

    async def mark_tour_seen(self, org_id: str, uid: str, at: datetime) -> None:
        self.tours[(org_id, uid)] = at

    async def count_members(self, org_id: str) -> int:
        return len(self.members.get(org_id, {}))

    async def list_bank_accounts(self, org_id: str) -> list[BankAccount]:
        return list(self.bank_accounts.get(org_id, {}).values())

    async def add_bank_account(self, org_id: str, new: NewBankAccount, event: AuditEvent) -> bool:
        async with self._txn:
            accounts = self.bank_accounts.setdefault(org_id, {})
            if new.account.account_id in accounts:
                return False
            accounts[new.account.account_id] = new.account
            self.account_hashes.setdefault(org_id, {})[new.account.account_id] = new.account_hash
            self.events.setdefault(org_id, []).append(event)
            return True

    async def save_bank_account(self, org_id: str, account: BankAccount) -> None:
        self.bank_accounts[org_id][account.account_id] = account

    async def delete_bank_account(self, org_id: str, account_id: str) -> bool:
        async with self._txn:
            if account_id not in self.bank_accounts.get(org_id, {}):
                return False
            del self.bank_accounts[org_id][account_id]
            self.account_hashes.get(org_id, {}).pop(account_id, None)
            return True


def demo_workspace(org_id: str) -> Workspace:
    """A ready-made workspace for tests that only need one to exist."""
    from datetime import UTC, datetime, timedelta

    from app.domain.models.workspace import Profile, Subscription

    now = datetime(2026, 10, 11, tzinfo=UTC)
    return Workspace(
        org_id=org_id,
        name="Synthetic Demo Ltd",
        entity_type="COMPANY",
        profile=Profile(legal_name="Synthetic Demo Ltd"),
        country="ID",
        timezone="Asia/Jakarta",
        currency="IDR",
        default_language="en",
        subscription=Subscription(
            plan_id="free_trial",
            status="TRIALING",
            trial_started_at=now,
            trial_ends_at=now + timedelta(days=30),
        ),
        created_by="u-demo",
        created_at=now,
    )
