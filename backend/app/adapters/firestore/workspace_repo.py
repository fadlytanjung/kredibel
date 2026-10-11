"""WorkspaceRepository on Firestore: one transaction per workspace creation (AC-013-2, AC-013-3).

Normative references: docs/09 §3.1–§3.4, §3.16, §3.18; docs/13 §2.2 (atomic audit).
"""

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import Any

from google.api_core.exceptions import Aborted
from google.cloud.firestore import AsyncClient, AsyncTransaction, async_transactional

from app.adapters.firestore.models.workspace import (
    AccountHashDoc,
    BankAccountDoc,
    EventDoc,
    MemberDoc,
    OrgDoc,
    SignupDoc,
    SignupUserDoc,
)
from app.domain.models.workspace import BankAccount, Profile, Subscription, Workspace
from app.ports.workspace_repository import (
    AlreadyMember,
    Created,
    CreateOutcome,
    NewWorkspace,
    SignupLimitReached,
    WorkspaceRepository,
)

_TXN_ATTEMPTS = 6


def _dump(model: Any) -> dict[str, Any]:
    return model.model_dump(by_alias=True, exclude_none=True)


def _is_contention(exc: Exception) -> bool:
    # The SDK reports a lost race as Aborted, or as ValueError once its own attempts run out.
    return isinstance(exc, Aborted) or (
        type(exc) is ValueError and str(exc).startswith("Failed to commit transaction")
    )


async def _with_backoff[T](attempt: Callable[[], Awaitable[T]]) -> T:
    """Run a single-attempt transaction until it commits, with jittered backoff.

    The SDK retries a conflicting transaction immediately, so two writers of the same hot
    documents (system/signup) can keep aborting each other. Random waits break the tie, and the
    loser re-reads and sees what the winner wrote.
    """
    for n in range(_TXN_ATTEMPTS):
        try:
            return await attempt()
        except Exception as exc:
            if not _is_contention(exc) or n == _TXN_ATTEMPTS - 1:
                raise
            await asyncio.sleep(random.uniform(0.05, 0.2) * (n + 1))
    raise AssertionError("unreachable")


class FirestoreWorkspaceRepository(WorkspaceRepository):
    def __init__(self, client: AsyncClient) -> None:
        self._db = client

    async def create_workspace(self, new: NewWorkspace, *, max_workspaces: int) -> CreateOutcome:
        db = self._db
        ws = new.workspace
        org_ref = db.collection("orgs").document(ws.org_id)
        signup_ref = db.collection("system").document("signup")
        user_ref = signup_ref.collection("users").document(new.owner.uid)

        @async_transactional
        async def run(txn: AsyncTransaction) -> CreateOutcome:
            # Every read happens before any write (Firestore transaction rule).
            user_snap = await user_ref.get(transaction=txn)
            if user_snap.exists:
                user = SignupUserDoc.model_validate(user_snap.to_dict())
                return AlreadyMember(org_id=user.org_id, role=user.role)
            signup_snap = await signup_ref.get(transaction=txn)
            created = SignupDoc.model_validate(signup_snap.to_dict() or {}).workspaces_created
            if created >= max_workspaces:
                return SignupLimitReached(created)

            txn.set(org_ref, _dump(self._org_doc(ws)))
            txn.set(
                org_ref.collection("members").document(new.owner.uid),
                _dump(
                    MemberDoc(
                        uid=new.owner.uid,
                        org_id=ws.org_id,
                        email=new.owner.email,
                        display_name=new.owner.display_name,
                        role=new.owner.role,
                        language=new.owner.language,
                        created_at=ws.created_at,
                    )
                ),
            )
            private = db.collection("orgPrivate").document(ws.org_id)
            for item in new.bank_accounts:
                acc = item.account
                txn.set(
                    org_ref.collection("bankAccounts").document(acc.account_id),
                    _dump(BankAccountDoc(org_id=ws.org_id, **acc.model_dump())),
                )
                txn.set(
                    private.collection("accountHashes").document(acc.account_id),
                    _dump(
                        AccountHashDoc(
                            org_id=ws.org_id, account_id=acc.account_id, hash=item.account_hash
                        )
                    ),
                )
            for event in new.events:
                txn.set(
                    org_ref.collection("events").document(event.event_id),
                    _dump(EventDoc(org_id=ws.org_id, **event.model_dump())),
                )
            txn.set(signup_ref, _dump(SignupDoc(workspaces_created=created + 1)))
            txn.set(
                user_ref,
                _dump(
                    SignupUserDoc(
                        uid=new.owner.uid,
                        org_id=ws.org_id,
                        role=new.owner.role,
                        created_at=ws.created_at,
                    )
                ),
            )
            return Created(ws.org_id)

        return await _with_backoff(lambda: run(db.transaction(max_attempts=1)))

    async def get_workspace(self, org_id: str) -> Workspace | None:
        snap = await self._db.collection("orgs").document(org_id).get()
        if not snap.exists:
            return None
        doc = OrgDoc.model_validate(snap.to_dict())
        return Workspace(
            org_id=doc.org_id,
            name=doc.name,
            entity_type=doc.entity_type,
            profile=Profile.model_validate(doc.profile),
            country=doc.country,
            timezone=doc.timezone,
            currency=doc.currency,
            default_language=doc.default_language,
            subscription=Subscription.model_validate(doc.subscription),
            share_verified_labels=bool(doc.learning.get("shareVerifiedLabels", False)),
            created_by=doc.created_by,
            created_at=doc.created_at,
        )

    async def list_bank_accounts(self, org_id: str) -> list[BankAccount]:
        query = self._db.collection("orgs").document(org_id).collection("bankAccounts")
        accounts: list[BankAccount] = []
        async for snap in query.stream():
            doc = BankAccountDoc.model_validate(snap.to_dict())
            accounts.append(BankAccount(**doc.model_dump(exclude={"org_id", "schema_version"})))
        return accounts

    @staticmethod
    def _org_doc(ws: Workspace) -> OrgDoc:
        return OrgDoc(
            org_id=ws.org_id,
            name=ws.name,
            entity_type=ws.entity_type,
            profile=ws.profile.model_dump(by_alias=True, exclude_none=True),
            country=ws.country,
            timezone=ws.timezone,
            currency=ws.currency,
            default_language=ws.default_language,
            subscription=ws.subscription.model_dump(by_alias=True, exclude_none=True),
            learning={"shareVerifiedLabels": ws.share_verified_labels},
            counts={"documents": 0, "openReviewItems": 0, "openFindingsBySeverity": {}},
            created_by=ws.created_by,
            created_at=ws.created_at,
        )
