"""Persistence of workspaces, members and bank accounts (spec 013 plan: WorkspaceRepository)."""

from dataclasses import dataclass, field
from typing import Protocol

from app.domain.models.events import AuditEvent
from app.domain.models.workspace import BankAccount, Workspace


@dataclass(frozen=True)
class OwnerMember:
    uid: str
    email: str | None
    display_name: str | None
    role: str = "owner"
    language: str = "en"


@dataclass(frozen=True)
class NewBankAccount:
    account: BankAccount
    # sha256(orgId:digits); stored only under orgPrivate/, never in a readable document.
    account_hash: str


@dataclass(frozen=True)
class NewWorkspace:
    workspace: Workspace
    owner: OwnerMember
    bank_accounts: list[NewBankAccount] = field(default_factory=list)
    events: list[AuditEvent] = field(default_factory=list)


@dataclass(frozen=True)
class Created:
    org_id: str


@dataclass(frozen=True)
class AlreadyMember:
    """The user already has a workspace (system/signup/users/{uid})."""

    org_id: str
    role: str


@dataclass(frozen=True)
class SignupLimitReached:
    workspaces_created: int


CreateOutcome = Created | AlreadyMember | SignupLimitReached


class WorkspaceRepository(Protocol):
    async def create_workspace(self, new: NewWorkspace, *, max_workspaces: int) -> CreateOutcome:
        """In one transaction: check the user and the signup counter, then write the org, the
        owner member, bank accounts with their private hashes, the events and the counters."""
        ...

    async def get_workspace(self, org_id: str) -> Workspace | None: ...

    async def list_bank_accounts(self, org_id: str) -> list[BankAccount]: ...
