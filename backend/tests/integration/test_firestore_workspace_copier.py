"""FirestoreWorkspaceCopier against the emulator (spec 021, AC-021-1, AC-021-2): every collection
of the template and its server-only records are copied with IDs and people swapped, the skipped
ones are not, the template's other fields are merged, the template is untouched, and a discard
removes the copy. Files (Cloud Storage) are not part of this test. Synthetic data only."""

import uuid
from datetime import UTC, datetime

import pytest
from google.cloud.firestore import AsyncClient

from app.adapters.firestore.workspace_copier import FirestoreWorkspaceCopier

AT = datetime(2026, 9, 30, 10, 0, tzinfo=UTC)
SWAP = {"org_demo_template": "org_01NEW", "u_template": "u-1"}


@pytest.fixture
def db(firestore_emulator: str) -> AsyncClient:
    return AsyncClient(project=f"test-{uuid.uuid4().hex[:12]}")


async def _seed(db: AsyncClient) -> None:
    org = db.collection("orgs").document("org_demo_template")
    await org.set(
        {
            "orgId": "org_demo_template",
            "name": "Sunrise Coffee Roasters",
            "counts": {"documents": 2},
            "ledgerMappings": {"lay_1": {"by": "u_template"}},
            "subscription": {"planId": "free_trial", "limitOverrides": {"documentsPerMonth": 600}},
        }
    )
    await (
        org.collection("documents")
        .document("doc_1")
        .set(
            {
                "orgId": "org_demo_template",
                "fileName": "statement-2026-06.pdf",
                "uploadedBy": "u_template",
                "gcsPath": "gs://docs/orgs/org_demo_template/documents/doc_1/original.pdf",
                "uploadedAt": AT,
            }
        )
    )
    await (
        org.collection("runs")
        .document("month-org_demo_template-2026-06-2")
        .set(
            {"orgId": "org_demo_template", "stages": [{"node": "explain_month", "tokensIn": 3400}]}
        )
    )
    await (
        org.collection("labels")
        .document("lbl_1")
        .set({"orgId": "org_demo_template", "task": "CATEGORY"})
    )
    await org.collection("members").document("u_template").set({"uid": "u_template"})
    await org.collection("events").document("evt_1").set({"type": "WORKSPACE_CREATED"})
    await (
        db.collection("orgPrivate")
        .document("org_demo_template")
        .collection("accountHashes")
        .document("acc_1")
        .set({"orgId": "org_demo_template", "hash": "h"})
    )
    # The new workspace's own record, as create_workspace writes it.
    await (
        db.collection("orgs")
        .document("org_01NEW")
        .set(
            {
                "orgId": "org_01NEW",
                "name": "Sunrise Coffee Roasters",
                "subscription": {"planId": "free_trial"},
            }
        )
    )


async def test_ac021_1_records_are_copied_with_ids_and_people_swapped(db, monkeypatch):
    copier = FirestoreWorkspaceCopier(db, "test", "unused")

    async def no_files(source: str, target: str) -> None:
        return None

    monkeypatch.setattr(copier, "_copy_files", no_files)
    await _seed(db)

    written = await copier.copy_records("org_demo_template", "org_01NEW", SWAP)
    await copier.copy_workspace_fields("org_demo_template", "org_01NEW", SWAP)

    new = db.collection("orgs").document("org_01NEW")
    doc = (await new.collection("documents").document("doc_1").get()).to_dict()
    assert written == 4, "documents, runs, labels and one account hash; not members or events"
    assert doc["orgId"] == "org_01NEW" and doc["uploadedBy"] == "u-1" and doc["uploadedAt"] == AT
    assert doc["gcsPath"] == "gs://docs/orgs/org_01NEW/documents/doc_1/original.pdf"
    assert (await new.collection("runs").document("month-org_01NEW-2026-06-2").get()).exists
    assert [s.id async for s in new.collection("members").stream()] == []
    assert [s.id async for s in new.collection("events").stream()] == []
    hashes = db.collection("orgPrivate").document("org_01NEW").collection("accountHashes")
    assert (await hashes.document("acc_1").get()).to_dict() == {"orgId": "org_01NEW", "hash": "h"}
    record = (await new.get()).to_dict()
    assert record["counts"] == {"documents": 2} and record["ledgerMappings"]["lay_1"]["by"] == "u-1"
    assert record["subscription"] == {"planId": "free_trial"}, (
        "the demo limits stay with the template"
    )
    template = (
        await db.collection("orgs")
        .document("org_demo_template")
        .collection("documents")
        .document("doc_1")
        .get()
    ).to_dict()
    assert template["orgId"] == "org_demo_template", "the template is never written"


async def test_ac021_2_a_discard_removes_the_copy(db, monkeypatch):
    copier = FirestoreWorkspaceCopier(db, "test", "unused")

    async def no_files(source: str, target: str) -> None:
        return None

    monkeypatch.setattr(copier, "_copy_files", no_files)
    monkeypatch.setattr(
        copier, "_get_bucket", lambda: type("B", (), {"list_blobs": lambda self, prefix: []})()
    )
    await _seed(db)
    await copier.copy_records("org_demo_template", "org_01NEW", SWAP)
    await copier.discard("org_01NEW")
    new = db.collection("orgs").document("org_01NEW")
    assert [c.id async for c in new.collections()] == []
    assert not (await new.get()).exists
    assert [c.id async for c in db.collection("orgs").document("org_demo_template").collections()]
