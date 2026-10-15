"""Persistence of workspaces, members and bank accounts (spec 013 plan: WorkspaceRepository)."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

from app.domain.models.events import AuditEvent
from app.domain.models.workspace import (
    BankAccount,
    Subscription,
    UsageDay,
    UsageMonth,
    Workspace,
)
from app.domain.plans import Decision


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

    async def save_workspace(self, workspace: Workspace, event: AuditEvent) -> None:
        """Replace the workspace's editable fields and append the event, atomically."""
        ...

    async def save_ledger_mapping(
        self, org_id: str, layout_signature: str, mapping: dict[str, Any], event: AuditEvent
    ) -> None:
        """A person's confirmed column mapping for one file layout (docs/09 §3.8), with its event;
        the next export with the same layout is parsed at once (AC-005-11)."""
        ...

    async def count_members(self, org_id: str) -> int: ...

    async def list_bank_accounts(self, org_id: str) -> list[BankAccount]: ...

    async def add_bank_account(self, org_id: str, new: NewBankAccount, event: AuditEvent) -> bool:
        """False when an account with this ID (same bank and number) already exists."""
        ...

    async def save_bank_account(self, org_id: str, account: BankAccount) -> None: ...

    async def delete_bank_account(self, org_id: str, account_id: str) -> bool:
        """False when there is no such account; removes its private hash too."""
        ...


@dataclass(frozen=True)
class UsageIncrement:
    documents_uploaded: int = 0
    pages_reserved: int = 0
    month_runs: int = 0
    assistant_questions: int = 0


@dataclass(frozen=True)
class PendingWrite:
    """A write the caller needs in the metering transaction (spec 003: the document record)."""

    path: str
    data: dict[str, Any]


@dataclass(frozen=True)
class UsageSettlement:
    """What a finished document run actually used; replaces its page reservation (AC-013-10)."""

    month: str
    pages_reserved: int
    pages_read: int
    pages_cached: int
    ocr_pages: int
    parser_pages: int
    ai_spend_usd: Decimal


Decide = Callable[[Subscription, UsageMonth, UsageDay], Decision]


class UsageRepository(Protocol):
    async def meter(
        self,
        org_id: str,
        *,
        month: str,
        day: str,
        decide: Decide,
        increment: UsageIncrement,
        writes: Sequence[PendingWrite] = (),
    ) -> tuple[Decision, Subscription]:
        """In one transaction: read the subscription and usage, decide, and only when allowed
        apply the increment and the caller's writes (AC-013-9)."""
        ...

    async def settle(self, org_id: str, settlement: UsageSettlement) -> None: ...

    async def get_usage(
        self, org_id: str, *, month: str, day: str
    ) -> tuple[UsageMonth, UsageDay]: ...
