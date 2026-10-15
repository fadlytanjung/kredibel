"""Profile suggestions (spec 014, AC-014-5): a person accepts or rejects; nothing changes before.

ACCEPT writes the value into the profile (a bank account gets its mask and the hash kept in
orgPrivate) and records SUGGESTION_ACCEPTED; REJECT records SUGGESTION_REJECTED, and the
deterministic ID keeps the same value from ever being suggested again.
"""

from dataclasses import replace

from app.core.auth import Principal
from app.core.clock import Clock
from app.core.ids import new_id
from app.domain.errors import NotFoundError, SuggestionAlreadyDecidedError
from app.domain.models.events import AuditEvent
from app.domain.models.workspace import Address, BankAccount
from app.domain.profile_suggestions import Suggestion
from app.ports.suggestion_repository import SuggestionRepository
from app.ports.workspace_repository import NewBankAccount, WorkspaceRepository

OWNER = "owner"


class SuggestionService:
    def __init__(
        self,
        *,
        suggestions: SuggestionRepository,
        workspaces: WorkspaceRepository,
        clock: Clock,
    ) -> None:
        self._suggestions = suggestions
        self._workspaces = workspaces
        self._clock = clock

    async def list_suggestions(self, org_id: str, *, status: str | None) -> list[Suggestion]:
        return await self._suggestions.list_suggestions(org_id, status=status)

    async def decide(
        self, principal: Principal, org_id: str, suggestion_id: str, decision: str
    ) -> Suggestion:
        suggestion = await self._suggestions.get(org_id, suggestion_id)
        if suggestion is None:
            raise NotFoundError("Suggestion not found", code="SUGGESTION_NOT_FOUND")
        if suggestion.status in ("ACCEPTED", "REJECTED"):
            raise SuggestionAlreadyDecidedError(suggestion_id, suggestion.status)
        now = self._clock.now()
        accepted = decision == "ACCEPT"
        if accepted:
            await self._apply(principal, org_id, suggestion)
        decided = replace(
            suggestion,
            status="ACCEPTED" if accepted else "REJECTED",
            decided_by=principal.uid,
            decided_at=now,
            secret={},
        )
        event = AuditEvent.model_validate(
            {
                "event_id": new_id("evt"),
                "type": "SUGGESTION_ACCEPTED" if accepted else "SUGGESTION_REJECTED",
                "actor_uid": principal.uid,
                "actor_role": principal.role or OWNER,
                "at": now,
                "subject": {"suggestionId": suggestion_id},
                "details": {"field": suggestion.field},
            }
        )
        await self._suggestions.decide(org_id, decided, event)
        return decided

    async def _apply(self, principal: Principal, org_id: str, suggestion: Suggestion) -> None:
        workspace = await self._workspaces.get_workspace(org_id)
        if workspace is None:
            raise NotFoundError("Workspace not found", code="WORKSPACE_NOT_FOUND")
        now = self._clock.now()
        value = suggestion.value
        if suggestion.field == "BANK_ACCOUNT":
            account_hash = suggestion.secret.get("accountHash")
            if not account_hash:
                raise NotFoundError("The account's hash is gone", code="SUGGESTION_SECRET_MISSING")
            account = BankAccount(
                account_id=new_id("acc"),
                bank_name=str(value.get("bankName") or ""),
                account_masked=str(value.get("accountMasked") or ""),
                holder_name=str(value.get("holderName") or workspace.name),
                source="DETECTED",
            )
            event = AuditEvent.model_validate(
                {
                    "event_id": new_id("evt"),
                    "type": "BANK_ACCOUNT_ADDED",
                    "actor_uid": principal.uid,
                    "actor_role": principal.role or OWNER,
                    "at": now,
                    "subject": {"accountId": account.account_id},
                    "details": {"source": "DETECTED", "suggestionId": suggestion.suggestion_id},
                }
            )
            await self._workspaces.add_bank_account(
                org_id, NewBankAccount(account=account, account_hash=account_hash), event
            )
            return
        profile = workspace.profile
        if suggestion.field == "TAX_ID":
            profile = profile.model_copy(
                update={"tax_id_masked": str(value.get("taxIdMasked") or "")}
            )
        elif suggestion.field == "ADDRESS":
            profile = profile.model_copy(
                update={"address": Address(line1=value.get("line1"), city=value.get("city"))}
            )
        else:
            return
        event = AuditEvent.model_validate(
            {
                "event_id": new_id("evt"),
                "type": "PROFILE_UPDATED",
                "actor_uid": principal.uid,
                "actor_role": principal.role or OWNER,
                "at": now,
                "subject": {"orgId": org_id},
                "details": {"fields": suggestion.field, "suggestionId": suggestion.suggestion_id},
            }
        )
        await self._workspaces.save_workspace(
            workspace.model_copy(update={"profile": profile}), event
        )
