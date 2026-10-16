"""Workspace use cases: create (spec 013 AC-013-2, AC-013-3).

Normative references: docs/09 §3.1–§3.4 and §3.18, docs/14 §4.1 and §6, ADR-011.
"""

from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import timedelta
from typing import Literal
from zoneinfo import available_timezones

from app.core.auth import Principal
from app.core.clock import Clock
from app.core.errors import (
    AlreadyInWorkspaceError,
    BankAccountExistsError,
    LanguageNotAvailableError,
    NotFoundError,
    SignupClosedError,
    ValidationProblem,
)
from app.core.ids import content_id, new_id
from app.domain.accounts import (
    account_digits,
    account_hash,
    account_id_parts,
    mask_account,
    mask_tax_id,
)
from app.domain.errors import DemoUnavailableError, ForbiddenError
from app.domain.models.events import AuditEvent
from app.domain.models.workspace import (
    BankAccount,
    BankAccountCreate,
    BankAccountUpdate,
    Profile,
    Subscription,
    Workspace,
    WorkspaceCreate,
    WorkspaceUpdate,
)
from app.domain.plans import PlanCatalog
from app.ports.identity_admin import IdentityAdmin
from app.ports.workspace_copier import WorkspaceCopier
from app.ports.workspace_repository import (
    AlreadyMember,
    Created,
    NewBankAccount,
    NewWorkspace,
    OwnerMember,
    WorkspaceRepository,
)

SignupMode = Literal["open", "invite_only", "closed"]
OWNER = "owner"


class WorkspaceService:
    def __init__(
        self,
        *,
        repo: WorkspaceRepository,
        identity: IdentityAdmin,
        plans: PlanCatalog,
        clock: Clock,
        signup_mode: SignupMode,
        max_workspaces: int,
        on_framework_change: Callable[[str, str], Awaitable[object]] | None = None,
        copier: WorkspaceCopier | None = None,
        demo_template_org: str = "",
        demo_account_email: str = "",
    ) -> None:
        self._repo = repo
        self._identity = identity
        self._plans = plans
        self._clock = clock
        self._signup_mode = signup_mode
        self._on_framework_change = on_framework_change
        self._max_workspaces = max_workspaces
        self._copier = copier
        self._demo_template_org = demo_template_org
        self._demo_account_email = demo_account_email.strip().lower()

    async def create(self, principal: Principal, request: WorkspaceCreate) -> Workspace:
        # A claim only counts while its workspace exists; a stale one (never created, or removed by
        # a demo reset) must not lock the user out of onboarding.
        if principal.org_id is not None and await self._repo.get_workspace(principal.org_id):
            raise AlreadyInWorkspaceError(principal.org_id)
        # P0 has no invites, so invite_only behaves like closed for creating a workspace.
        if self._signup_mode != "open":
            raise SignupClosedError()
        if request.timezone not in available_timezones():
            raise ValidationProblem("timezone", "Unknown time zone")

        new = self._new_workspace(principal, request)
        outcome = await self._repo.create_workspace(new, max_workspaces=self._max_workspaces)

        if isinstance(outcome, Created):
            # Claims only after the commit: a token must never name a workspace that does not exist.
            await self._identity.set_claims(principal.uid, {"orgId": outcome.org_id, "role": OWNER})
            return new.workspace
        if isinstance(outcome, AlreadyMember):
            # A double submit, or claims lost after an earlier commit: point the token at the
            # workspace that exists, and let the client refresh.
            await self._identity.set_claims(
                principal.uid, {"orgId": outcome.org_id, "role": outcome.role}
            )
            raise AlreadyInWorkspaceError(outcome.org_id)
        raise SignupClosedError()

    @property
    def demo_available(self) -> bool:
        return bool(self._demo_template_org and self._copier is not None)

    async def reset_demo_account(self, principal: Principal) -> Workspace:
        """Spec 024, AC-024-3: the public demo account's workspace replaced by a fresh copy of the
        demo company; nobody else's workspace can be reset this way."""
        email = (principal.email or "").strip().lower()
        if not self._demo_account_email or email != self._demo_account_email:
            raise ForbiddenError("Only the demo account can be reset.")
        if not self.demo_available or self._copier is None:
            raise DemoUnavailableError()
        if principal.org_id is not None and principal.org_id != self._demo_template_org:
            await self._copier.discard(principal.org_id)
        return await self.create_demo(principal.model_copy(update={"org_id": None, "role": None}))

    async def create_demo(self, principal: Principal) -> Workspace:
        """Spec 021: a new workspace, owned by the principal, holding a copy of the demo template's
        records and files; the rules for a new workspace apply, and a failed copy leaves nothing."""
        if principal.org_id is not None and await self._repo.get_workspace(principal.org_id):
            raise AlreadyInWorkspaceError(principal.org_id)
        if self._signup_mode != "open":
            raise SignupClosedError()
        if not self.demo_available or self._copier is None:
            raise DemoUnavailableError()
        template = await self._repo.get_workspace(self._demo_template_org)
        if template is None:
            raise DemoUnavailableError()

        request = WorkspaceCreate(
            name=template.name,
            profile=template.profile,
            timezone=template.timezone,
            currency=template.currency,
        )
        made = self._new_workspace(principal, request)
        new = replace(
            made,
            workspace=made.workspace.model_copy(
                update={"entity_type": template.entity_type, "country": template.country}
            ),
        )
        org_id = new.workspace.org_id
        new.events.append(
            self._event("DEMO_COPIED", principal, {"orgId": org_id, "fromOrgId": template.org_id})
        )
        swap = {template.org_id: org_id, template.created_by: principal.uid}
        try:
            await self._copier.copy_records(template.org_id, org_id, swap)
            outcome = await self._repo.create_workspace(new, max_workspaces=self._max_workspaces)
            if isinstance(outcome, Created):
                await self._copier.copy_workspace_fields(template.org_id, org_id, swap)
        except Exception:
            await self._copier.discard(org_id)
            raise
        if isinstance(outcome, Created):
            await self._identity.set_claims(principal.uid, {"orgId": org_id, "role": OWNER})
            return new.workspace
        await self._copier.discard(org_id)
        if isinstance(outcome, AlreadyMember):
            await self._identity.set_claims(
                principal.uid, {"orgId": outcome.org_id, "role": outcome.role}
            )
            raise AlreadyInWorkspaceError(outcome.org_id)
        raise SignupClosedError()

    async def get(self, org_id: str) -> Workspace:
        workspace = await self._repo.get_workspace(org_id)
        if workspace is None:
            raise NotFoundError()
        return workspace

    async def tour_seen(self, principal: Principal) -> bool:
        """Spec 021: the guided tour starts by itself until this person finishes or skips it."""
        if principal.org_id is None:
            return False
        return await self._repo.tour_seen(principal.org_id, principal.uid)

    async def mark_tour_seen(self, principal: Principal) -> None:
        if principal.org_id is not None:
            await self._repo.mark_tour_seen(principal.org_id, principal.uid, self._clock.now())

    async def seats_used(self, org_id: str) -> int:
        return await self._repo.count_members(org_id)

    async def update(self, principal: Principal, org_id: str, patch: WorkspaceUpdate) -> Workspace:
        current = await self.get(org_id)
        if patch.timezone is not None and patch.timezone not in available_timezones():
            raise ValidationProblem("timezone", "Unknown time zone")
        if patch.default_language is not None:
            self._check_language(patch.default_language)

        updates: dict[str, object] = {}
        changed = sorted(patch.model_dump(exclude_unset=True, by_alias=True))
        if patch.name is not None:
            updates["name"] = patch.name
        if patch.timezone is not None:
            updates["timezone"] = patch.timezone
        if patch.default_language is not None:
            updates["default_language"] = patch.default_language
        if patch.learning is not None:
            updates["share_verified_labels"] = patch.learning.share_verified_labels
        if patch.goal is not None:
            updates["goal"] = patch.goal
        if patch.expectations is not None:
            months = [e.month for e in patch.expectations]
            if len(set(months)) != len(months):
                raise ValidationProblem("expectations", "One expectation per month.")
            updates["expectations"] = sorted(patch.expectations, key=lambda e: e.month)
        profile_updates = patch.profile.model_dump(exclude_unset=True) if patch.profile else {}
        profile_updates.pop("tax_id_masked", None)  # read-only; set from taxId only
        if patch.tax_id is not None:
            profile_updates["tax_id_masked"] = mask_tax_id(patch.tax_id)
        if profile_updates:
            updates["profile"] = current.profile.model_copy(update=profile_updates)

        updated = current.model_copy(update=updates)
        event = self._event("PROFILE_UPDATED", principal, {"orgId": org_id})
        event = event.model_copy(update={"details": {"fields": ",".join(changed)}})
        await self._repo.save_workspace(updated, event)
        before, after = current.profile.accounting_framework, updated.profile.accounting_framework
        if after != before and self._on_framework_change is not None:
            await self._on_framework_change(org_id, after)
        return updated

    def _check_language(self, language: str) -> None:
        catalog = {lang.code: lang.status for lang in self._plans.languages}
        if language not in catalog:
            raise ValidationProblem("defaultLanguage", "Unknown language")
        if catalog[language] != "available":
            raise LanguageNotAvailableError(language)

    async def list_bank_accounts(self, org_id: str) -> list[BankAccount]:
        return await self._repo.list_bank_accounts(org_id)

    async def add_bank_account(
        self, principal: Principal, org_id: str, request: BankAccountCreate
    ) -> BankAccount:
        [new] = self._bank_accounts(org_id, [request])
        event = self._event("BANK_ACCOUNT_ADDED", principal, {"accountId": new.account.account_id})
        if not await self._repo.add_bank_account(org_id, new, event):
            raise BankAccountExistsError(new.account.account_id)
        return new.account

    async def update_bank_account(
        self, org_id: str, account_id: str, patch: BankAccountUpdate
    ) -> BankAccount:
        accounts = {a.account_id: a for a in await self._repo.list_bank_accounts(org_id)}
        if account_id not in accounts:
            raise NotFoundError()
        updated = accounts[account_id].model_copy(update=patch.model_dump(exclude_unset=True))
        await self._repo.save_bank_account(org_id, updated)
        return updated

    async def delete_bank_account(self, org_id: str, account_id: str) -> None:
        # Spec 003 adds the "no statement uses it" check once statements exist.
        if not await self._repo.delete_bank_account(org_id, account_id):
            raise NotFoundError()

    def _new_workspace(self, principal: Principal, request: WorkspaceCreate) -> NewWorkspace:
        now = self._clock.now()
        org_id = new_id("org")
        plan = self._plans.plan(self._plans.default_plan)
        trial_days = plan.trial_days or 0

        profile = request.profile or Profile()
        profile = profile.model_copy(
            update={
                "legal_name": profile.legal_name or request.name,
                "tax_id_masked": mask_tax_id(request.tax_id) if request.tax_id else None,
            }
        )
        workspace = Workspace(
            org_id=org_id,
            name=request.name,
            entity_type=request.entity_type,
            profile=profile,
            country=request.country,
            timezone=request.timezone,
            currency=request.currency,
            default_language="en",
            subscription=Subscription(
                plan_id=plan.id,
                status="TRIALING",
                trial_started_at=now,
                trial_ends_at=now + timedelta(days=trial_days),
            ),
            created_by=principal.uid,
            created_at=now,
        )

        accounts = self._bank_accounts(org_id, request.bank_accounts)
        events = [self._event("WORKSPACE_CREATED", principal, {"orgId": org_id})]
        events += [
            self._event("BANK_ACCOUNT_ADDED", principal, {"accountId": a.account.account_id})
            for a in accounts
        ]
        owner = OwnerMember(
            uid=principal.uid, email=principal.email, display_name=principal.display_name
        )
        return NewWorkspace(workspace=workspace, owner=owner, bank_accounts=accounts, events=events)

    @staticmethod
    def _bank_accounts(org_id: str, requested: list[BankAccountCreate]) -> list[NewBankAccount]:
        accounts: list[NewBankAccount] = []
        seen: set[str] = set()
        for item in requested:
            digits = account_digits(item.account_number)
            account_id = content_id("acc", *account_id_parts(org_id, item.bank_name, digits))
            if account_id in seen:
                raise ValidationProblem("bankAccounts", "The same account is listed twice")
            seen.add(account_id)
            account = BankAccount(
                account_id=account_id,
                bank_name=item.bank_name,
                account_masked=mask_account(digits),
                holder_name=item.holder_name,
                nickname=item.nickname,
                ledger_account_code=item.ledger_account_code,
            )
            accounts.append(
                NewBankAccount(account=account, account_hash=account_hash(org_id, digits))
            )
        return accounts

    def _event(self, kind: str, principal: Principal, subject: dict[str, str]) -> AuditEvent:
        # P0 has one role; P1 reads it from the principal's claim.
        return AuditEvent.model_validate(
            {
                "event_id": new_id("evt"),
                "type": kind,
                "actor_uid": principal.uid,
                "actor_role": principal.role or OWNER,
                "at": self._clock.now(),
                "subject": subject,
            }
        )
