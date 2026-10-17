"""WorkspaceRepository on Firestore: one transaction per workspace creation (AC-013-2, AC-013-3).

Normative references: docs/09 §3.1–§3.4, §3.16, §3.18; docs/13 §2.2 (atomic audit).
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

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
from app.adapters.firestore.txn import dump, with_backoff
from app.domain.models.events import AuditEvent
from app.domain.models.workspace import (
    BankAccount,
    MonthExpectation,
    Profile,
    Subscription,
    Workspace,
)
from app.ports.workspace_repository import (
    AlreadyMember,
    Created,
    CreateOutcome,
    NewBankAccount,
    NewWorkspace,
    SignupLimitReached,
    WorkspaceRepository,
)


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
                existing = db.collection("orgs").document(user.org_id)
                # A record whose workspace was removed (a demo reset) is stale; replace it.
                if (await existing.get(transaction=txn)).exists:
                    return AlreadyMember(org_id=user.org_id, role=user.role)
            signup_snap = await signup_ref.get(transaction=txn)
            created = SignupDoc.model_validate(signup_snap.to_dict() or {}).workspaces_created
            if created >= max_workspaces:
                return SignupLimitReached(created)

            txn.set(org_ref, dump(self._org_doc(ws)))
            txn.set(
                org_ref.collection("members").document(new.owner.uid),
                dump(
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
                    dump(BankAccountDoc(org_id=ws.org_id, **acc.model_dump())),
                )
                txn.set(
                    private.collection("accountHashes").document(acc.account_id),
                    dump(
                        AccountHashDoc(
                            org_id=ws.org_id, account_id=acc.account_id, hash=item.account_hash
                        )
                    ),
                )
            for event in new.events:
                txn.set(
                    org_ref.collection("events").document(event.event_id),
                    dump(EventDoc(org_id=ws.org_id, **event.model_dump())),
                )
            txn.set(signup_ref, dump(SignupDoc(workspaces_created=created + 1)))
            txn.set(
                user_ref,
                dump(
                    SignupUserDoc(
                        uid=new.owner.uid,
                        org_id=ws.org_id,
                        role=new.owner.role,
                        created_at=ws.created_at,
                    )
                ),
            )
            return Created(ws.org_id)

        return await with_backoff(lambda: run(db.transaction(max_attempts=1)))

    async def seed_workspace(self, new: NewWorkspace) -> None:
        """Server-side upsert for the demo workspace (scripts/seed_demo_workspace.py, AC-013-4).

        Not part of the port: no sign-up checks, and it does not count against MAX_WORKSPACES.
        """
        ws = new.workspace
        org_ref = self._db.collection("orgs").document(ws.org_id)
        batch = self._db.batch()
        batch.set(org_ref, dump(self._org_doc(ws)))
        batch.set(
            org_ref.collection("members").document(new.owner.uid),
            dump(
                MemberDoc(
                    uid=new.owner.uid,
                    org_id=ws.org_id,
                    email=new.owner.email,
                    display_name=new.owner.display_name,
                    role=new.owner.role,
                    created_at=ws.created_at,
                )
            ),
        )
        batch.set(
            self._db.collection("system")
            .document("signup")
            .collection("users")
            .document(new.owner.uid),
            dump(
                SignupUserDoc(
                    uid=new.owner.uid,
                    org_id=ws.org_id,
                    role=new.owner.role,
                    created_at=ws.created_at,
                )
            ),
        )
        await batch.commit()

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
            ledger_mappings=dict(doc.ledger_mappings or {}),
            goal=doc.goal,  # type: ignore[arg-type]
            expectations=[_expectation(e) for e in doc.expectations],
            created_by=doc.created_by,
            created_at=doc.created_at,
        )

    async def save_ledger_mapping(
        self, org_id: str, layout_signature: str, mapping: dict[str, Any], event: AuditEvent
    ) -> None:
        org_ref = self._db.collection("orgs").document(org_id)
        batch = self._db.batch()
        batch.update(org_ref, {f"ledgerMappings.{layout_signature}": mapping})
        batch.set(
            org_ref.collection("events").document(event.event_id),
            dump(EventDoc(org_id=org_id, **event.model_dump())),
        )
        await batch.commit()

    async def save_workspace(self, workspace: Workspace, event: AuditEvent) -> None:
        org_ref = self._db.collection("orgs").document(workspace.org_id)
        # Only the editable fields; counts and the subscription are owned by other writers.
        fields = {
            "name": workspace.name,
            "profile": workspace.profile.model_dump(by_alias=True, exclude_none=True),
            "timezone": workspace.timezone,
            "defaultLanguage": workspace.default_language,
            "learning": {"shareVerifiedLabels": workspace.share_verified_labels},
            "goal": workspace.goal,
            "expectations": [_expectation_doc(e) for e in workspace.expectations],
        }
        batch = self._db.batch()
        batch.update(org_ref, fields)
        batch.set(
            org_ref.collection("events").document(event.event_id),
            dump(EventDoc(org_id=workspace.org_id, **event.model_dump())),
        )
        await batch.commit()

    async def tour_seen(self, org_id: str, uid: str) -> bool:
        snap = (
            await self._db.collection("orgs")
            .document(org_id)
            .collection("members")
            .document(uid)
            .get()
        )
        return bool(snap.exists and (snap.to_dict() or {}).get("tourSeenAt"))

    async def mark_tour_seen(self, org_id: str, uid: str, at: datetime) -> None:
        member = self._db.collection("orgs").document(org_id).collection("members").document(uid)
        await member.set({"tourSeenAt": at}, merge=True)

    async def count_members(self, org_id: str) -> int:
        members = self._db.collection("orgs").document(org_id).collection("members")
        result = await members.count().get()
        return int(result[0][0].value)

    async def add_bank_account(self, org_id: str, new: NewBankAccount, event: AuditEvent) -> bool:
        org_ref = self._db.collection("orgs").document(org_id)
        acc = new.account
        account_ref = org_ref.collection("bankAccounts").document(acc.account_id)
        hash_ref = (
            self._db.collection("orgPrivate")
            .document(org_id)
            .collection("accountHashes")
            .document(acc.account_id)
        )

        @async_transactional
        async def run(txn: AsyncTransaction) -> bool:
            if (await account_ref.get(transaction=txn)).exists:
                return False
            txn.set(account_ref, dump(BankAccountDoc(org_id=org_id, **acc.model_dump())))
            txn.set(
                hash_ref,
                dump(
                    AccountHashDoc(org_id=org_id, account_id=acc.account_id, hash=new.account_hash)
                ),
            )
            txn.set(
                org_ref.collection("events").document(event.event_id),
                dump(EventDoc(org_id=org_id, **event.model_dump())),
            )
            return True

        return await with_backoff(lambda: run(self._db.transaction(max_attempts=1)))

    async def save_bank_account(self, org_id: str, account: BankAccount) -> None:
        ref = self._db.document(f"orgs/{org_id}/bankAccounts/{account.account_id}")
        await ref.set(dump(BankAccountDoc(org_id=org_id, **account.model_dump())))

    async def delete_bank_account(self, org_id: str, account_id: str) -> bool:
        ref = self._db.document(f"orgs/{org_id}/bankAccounts/{account_id}")
        if not (await ref.get()).exists:
            return False
        batch = self._db.batch()
        batch.delete(ref)
        batch.delete(self._db.document(f"orgPrivate/{org_id}/accountHashes/{account_id}"))
        await batch.commit()
        return True

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


def _minor(value: Decimal | None) -> int | None:
    return None if value is None else int((value * 100).to_integral_value())


def _expectation_doc(e: MonthExpectation) -> dict[str, Any]:
    out: dict[str, Any] = {"month": e.month}
    if e.money_in is not None:
        out["moneyInMinor"] = _minor(e.money_in)
    if e.money_out is not None:
        out["moneyOutMinor"] = _minor(e.money_out)
    return out


def _expectation(raw: dict[str, Any]) -> MonthExpectation:
    def major(key: str) -> Decimal | None:
        value = raw.get(key)
        return None if value is None else Decimal(int(value)) / 100

    return MonthExpectation(
        month=str(raw.get("month")),
        money_in=major("moneyInMinor"),
        money_out=major("moneyOutMinor"),
    )
