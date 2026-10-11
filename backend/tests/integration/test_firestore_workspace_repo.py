"""FirestoreWorkspaceRepository against the emulator (T013-06, AC-013-2, AC-013-3)."""

import asyncio
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from google.cloud.firestore import AsyncClient

from app.adapters.firestore.workspace_repo import FirestoreWorkspaceRepository
from app.adapters.policy_files import load_plans
from app.core.auth import Principal
from app.core.errors import AlreadyInWorkspaceError, SignupClosedError
from app.domain.models.workspace import WorkspaceCreate
from app.services.workspace_service import WorkspaceService
from tests.fakes.clock import FixedClock
from tests.fakes.identity_admin import FakeIdentityAdmin

PLANS = load_plans(Path(__file__).resolve().parents[3] / "contracts" / "plans.v1.yaml")
REQUEST = WorkspaceCreate.model_validate(
    {
        "name": "Synthetic Roasters Ltd",
        "entityType": "COMPANY",
        "timezone": "Asia/Jakarta",
        "bankAccounts": [
            {"bankName": "Bank Sintetis", "accountNumber": "1234564821", "holderName": "SR"}
        ],
    }
)


@pytest.fixture
def db(firestore_emulator: str) -> AsyncClient:
    # A fresh project per test isolates the signup counter and every path.
    return AsyncClient(project=f"test-{uuid.uuid4().hex[:12]}")


def _service(
    db: AsyncClient, max_workspaces: int = 15
) -> tuple[WorkspaceService, FakeIdentityAdmin]:
    identity = FakeIdentityAdmin()
    service = WorkspaceService(
        repo=FirestoreWorkspaceRepository(db),
        identity=identity,
        plans=PLANS,
        clock=FixedClock(datetime(2026, 10, 11, tzinfo=UTC)),
        signup_mode="open",
        max_workspaces=max_workspaces,
    )
    return service, identity


async def test_ac013_2_one_transaction_writes_every_document(db):
    service, _ = _service(db)

    ws = await service.create(Principal(uid="u-1", email="o@example.test"), REQUEST)

    org = (await db.collection("orgs").document(ws.org_id).get()).to_dict()
    assert org is not None
    assert org["schemaVersion"] == 1
    assert org["entityType"] == "COMPANY"
    assert org["subscription"]["status"] == "TRIALING"
    member = (await db.document(f"orgs/{ws.org_id}/members/u-1").get()).to_dict()
    assert member is not None and member["role"] == "owner"
    [account] = [
        s.to_dict() async for s in db.collection(f"orgs/{ws.org_id}/bankAccounts").stream()
    ]
    assert account is not None and account["accountMasked"] == "••••4821"
    assert "1234564821" not in str(account)
    [hashed] = [
        s.to_dict() async for s in db.collection(f"orgPrivate/{ws.org_id}/accountHashes").stream()
    ]
    assert hashed is not None and len(hashed["hash"]) == 64
    events = [s.to_dict() async for s in db.collection(f"orgs/{ws.org_id}/events").stream()]
    assert sorted(e["type"] for e in events if e) == ["BANK_ACCOUNT_ADDED", "WORKSPACE_CREATED"]
    signup = (await db.document("system/signup").get()).to_dict()
    assert signup is not None and signup["workspacesCreated"] == 1

    read_back = await FirestoreWorkspaceRepository(db).get_workspace(ws.org_id)
    assert read_back == ws


async def test_ac013_3_a_double_submit_creates_one_workspace(db):
    service, _ = _service(db)
    user = Principal(uid="u-1", email="o@example.test")

    results = await asyncio.gather(
        service.create(user, REQUEST), service.create(user, REQUEST), return_exceptions=True
    )

    assert sum(isinstance(r, AlreadyInWorkspaceError) for r in results) == 1
    orgs = [s async for s in db.collection("orgs").stream()]
    assert len(orgs) == 1


async def test_ac013_3_the_last_workspace_goes_to_exactly_one_user(db):
    service, _ = _service(db, max_workspaces=1)

    results = await asyncio.gather(
        service.create(Principal(uid="u-1"), REQUEST),
        service.create(Principal(uid="u-2"), REQUEST),
        return_exceptions=True,
    )

    assert sum(isinstance(r, SignupClosedError) for r in results) == 1
    orgs = [s async for s in db.collection("orgs").stream()]
    assert len(orgs) == 1


async def test_ac013_14_profile_update_and_bank_accounts_on_firestore(db):
    from app.core.errors import BankAccountExistsError
    from app.domain.models.workspace import BankAccountCreate, BankAccountUpdate, WorkspaceUpdate

    service, _ = _service(db)
    owner = Principal(uid="u-1", role="owner")
    ws = await service.create(owner, REQUEST)
    org = ws.org_id
    owner = owner.model_copy(update={"org_id": org})

    updated = await service.update(
        owner,
        org,
        WorkspaceUpdate.model_validate({"profile": {"tradingName": "SR"}, "taxId": "1234567890"}),
    )
    assert updated.profile.trading_name == "SR"
    assert (await FirestoreWorkspaceRepository(db).get_workspace(org)) == updated
    assert await service.seats_used(org) == 1

    extra = BankAccountCreate.model_validate(
        {"bankName": "Bank Dua", "accountNumber": "9876543210", "holderName": "SR"}
    )
    added = await service.add_bank_account(owner, org, extra)
    with pytest.raises(BankAccountExistsError):
        await service.add_bank_account(owner, org, extra)
    await service.update_bank_account(
        org, added.account_id, BankAccountUpdate.model_validate({"nickname": "Payroll"})
    )
    accounts = {a.account_id: a for a in await service.list_bank_accounts(org)}
    assert accounts[added.account_id].nickname == "Payroll"

    await service.delete_bank_account(org, added.account_id)
    assert added.account_id not in {a.account_id for a in await service.list_bank_accounts(org)}
    hash_doc = await db.document(f"orgPrivate/{org}/accountHashes/{added.account_id}").get()
    assert not hash_doc.exists
