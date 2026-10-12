"""The exact-duplicate claim is one Firestore transaction (spec 003 plan, docs/09 §3.18)."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from google.cloud.firestore import AsyncClient

from app.adapters.firestore.document_repo import FirestoreDocumentRepository

NOW = datetime(2026, 10, 12, 1, 57, tzinfo=UTC)
SHA = "a" * 64


@pytest.fixture
def repo(firestore_emulator: str) -> tuple[FirestoreDocumentRepository, AsyncClient]:
    db = AsyncClient(project=f"test-{uuid.uuid4().hex[:12]}")
    return FirestoreDocumentRepository(db), db


async def test_of_two_simultaneous_claims_exactly_one_wins(repo):
    docs, _db = repo
    results = await asyncio.gather(
        docs.claim_original("org_1", SHA, "doc_a", NOW),
        docs.claim_original("org_1", SHA, "doc_b", NOW),
    )
    assert results.count(None) == 1
    [holder] = [r for r in results if r is not None]
    assert holder in {"doc_a", "doc_b"}


async def test_a_released_claim_can_be_taken_again(repo):
    docs, _db = repo
    assert await docs.claim_original("org_1", SHA, "doc_a", NOW) is None
    await docs.release_original("org_1", SHA, "doc_a")
    assert await docs.claim_original("org_1", SHA, "doc_b", NOW) is None


async def test_release_never_drops_someone_elses_claim(repo):
    docs, _db = repo
    assert await docs.claim_original("org_1", SHA, "doc_a", NOW) is None
    await docs.release_original("org_1", SHA, "doc_b")
    assert await docs.claim_original("org_1", SHA, "doc_c", NOW) == "doc_a"


async def test_a_stale_claim_without_its_document_is_taken_over(repo):
    docs, _db = repo
    assert await docs.claim_original("org_1", SHA, "doc_a", NOW) is None
    later = NOW + timedelta(minutes=11)
    assert await docs.claim_original("org_1", SHA, "doc_b", later) is None


async def test_a_legacy_original_is_registered_on_first_sight(repo):
    docs, db = repo
    await db.document("orgs/org_1/documents/doc_old").set({"sha256": SHA, "docId": "doc_old"})
    assert await docs.claim_original("org_1", SHA, "doc_new", NOW) == "doc_old"
    claim = (await db.document(f"orgs/org_1/fileHashes/{SHA}").get()).to_dict()
    assert claim is not None and claim["docId"] == "doc_old"
