"""Support-only currency change (ADR-020): allowed on a workspace without documents, refused with
documents unless forced, always audited."""

import uuid
from datetime import UTC, datetime

import pytest
from google.cloud.firestore import AsyncClient

from app.adapters.firestore.workspace_repo import FirestoreWorkspaceRepository
from app.ports.workspace_repository import NewWorkspace, OwnerMember
from scripts.set_workspace_currency import CurrencyChangeRefused, set_workspace_currency
from tests.fakes.workspace_repository import demo_workspace

NOW = datetime(2026, 10, 12, tzinfo=UTC)


@pytest.fixture
async def db(firestore_emulator: str) -> AsyncClient:
    client = AsyncClient(project=f"test-{uuid.uuid4().hex[:12]}")
    repo = FirestoreWorkspaceRepository(client)
    await repo.seed_workspace(
        NewWorkspace(
            workspace=demo_workspace("org_c"),
            owner=OwnerMember(uid="u-1", email=None, display_name=None),
        )
    )
    return client


async def test_adr020_support_changes_the_currency_of_an_empty_workspace(db):
    result = await set_workspace_currency(db, "org_c", "MYR", actor="support", now=NOW)

    org = (await db.document("orgs/org_c").get()).to_dict()
    assert org is not None and org["currency"] == "MYR"
    assert result == {"orgId": "org_c", "from": "IDR", "to": "MYR", "documents": 0}
    events = [s.to_dict() async for s in db.collection("orgs/org_c/events").stream()]
    assert [e["type"] for e in events if e] == ["CURRENCY_CHANGED"]


async def test_adr020_documents_block_the_change_unless_forced(db):
    await db.document("orgs/org_c/documents/doc_1").set({"orgId": "org_c", "status": "DONE"})

    with pytest.raises(CurrencyChangeRefused, match="1 document"):
        await set_workspace_currency(db, "org_c", "MYR", actor="support", now=NOW)
    org = (await db.document("orgs/org_c").get()).to_dict()
    assert org is not None and org["currency"] == "IDR"

    await set_workspace_currency(db, "org_c", "MYR", actor="support", now=NOW, force=True)
    org = (await db.document("orgs/org_c").get()).to_dict()
    assert org is not None and org["currency"] == "MYR"
