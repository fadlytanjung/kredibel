"""Workspace use cases: create (spec 013 AC-013-2, AC-013-3).

Normative references: docs/09 §3.1–§3.4 and §3.18, docs/14 §4.1 and §6, ADR-011.
"""

from datetime import timedelta
from typing import Literal
from zoneinfo import available_timezones

from app.core.auth import Principal
from app.core.clock import Clock
from app.core.errors import AlreadyInWorkspaceError, SignupClosedError, ValidationProblem
from app.core.ids import content_id, new_id
from app.domain.accounts import (
    account_digits,
    account_hash,
    account_id_parts,
    mask_account,
    mask_tax_id,
)
from app.domain.models.events import AuditEvent
from app.domain.models.workspace import (
    BankAccount,
    BankAccountCreate,
    Profile,
    Subscription,
    Workspace,
    WorkspaceCreate,
)
from app.domain.plans import PlanCatalog
from app.ports.identity_admin import IdentityAdmin
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
    ) -> None:
        self._repo = repo
        self._identity = identity
        self._plans = plans
        self._clock = clock
        self._signup_mode = signup_mode
        self._max_workspaces = max_workspaces

    async def create(self, principal: Principal, request: WorkspaceCreate) -> Workspace:
        if principal.org_id is not None:
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
            currency="IDR",
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
        return AuditEvent.model_validate(
            {
                "event_id": new_id("evt"),
                "type": kind,
                "actor_uid": principal.uid,
                "actor_role": OWNER,
                "at": self._clock.now(),
                "subject": subject,
            }
        )
