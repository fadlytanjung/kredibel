"""A document whose kind the classifier is not sure of (spec 005, AC-005-2; spec 006, AC-006-9;
spec 009): E03 as a finding with its CONFIRM_TYPE item, the person's choice kept over the
classifier's, and the workflow continues. Synthetic data only."""

from datetime import UTC, datetime
from decimal import Decimal

from app.adapters.cloud_tasks import InlineTaskQueue
from app.domain.findings import Evidence, Finding, finding_id
from app.domain.models.document import DocStatus, DocType, Document
from app.domain.review_items import confirm_type_item
from tests.integration.test_invoice_workflow import AUTH, _client, _deps

ORG, DOC = "org_1", "doc_photo"
NOW = datetime(2026, 4, 2, tzinfo=UTC)


async def _seed(deps) -> str:
    """A photographed page stopped at NEEDS_INPUT by the classifier, with its finding and item."""
    doc = Document(
        doc_id=DOC,
        file_name="IMG_4471.jpg",
        content_type="image/jpeg",
        size_bytes=1200,
        page_count=1,
        sha256="e" * 64,
        gcs_path=f"gs://synthetic/{DOC}.jpg",
        uploaded_by="u-1",
        uploaded_at=NOW,
        doc_type=DocType.UNKNOWN,
        type_confidence=Decimal("0.42"),
        status=DocStatus.NEEDS_INPUT,
        status_detail="E03_UNCERTAIN_TYPE",
    )
    await deps.doc_repo.save_document(ORG, doc)
    finding = Finding(
        finding_id=finding_id("E03_UNCERTAIN_TYPE", DOC),
        code="E03_UNCERTAIN_TYPE",
        category="EXTRACTION",
        severity="LOW",
        title="Kredibel is not sure what kind of document this is",
        facts={"docType": "RECEIPT", "confidence": "0.42"},
        evidence=[Evidence(doc_id=DOC, page=1, label="Page 1")],
        doc_id=DOC,
    )
    await deps.findings.replace_document_findings(
        ORG, DOC, [finding], run_id=None, categories={"EXTRACTION"}
    )
    item = confirm_type_item(DOC, "IMG_4471.jpg", guess="RECEIPT", confidence="0.42")
    await deps.review_items.upsert_review_item(ORG, item)
    return item.item_id


async def test_ac005_2_the_type_is_asked_once_and_the_person_s_choice_wins():
    deps, _ = _deps()
    item_id = await _seed(deps)
    async with _client(deps) as client:
        queue = (
            await client.get("/api/review-items", params={"status": "OPEN"}, headers=AUTH)
        ).json()
        [listed] = queue["items"]
        assert listed["kind"] == "CONFIRM_TYPE" and listed["allowedActions"] == ["SET_TYPE"]
        assert listed["suggestion"]["docType"] == "RECEIPT" and listed["month"] is None
        assert listed["suggestion"]["confidence"] == "0.42"
        assert listed["title"] == "What kind of document is IMG_4471.jpg?"

        # No type, or "unknown", is not a choice.
        for body in ({"action": "SET_TYPE"}, {"action": "SET_TYPE", "docType": "UNKNOWN"}):
            refused = await client.post(
                f"/api/review-items/{item_id}/resolve", json=body, headers=AUTH
            )
            assert refused.status_code == 422, refused.text

        res = await client.post(
            f"/api/review-items/{item_id}/resolve",
            json={"action": "SET_TYPE", "docType": "RECEIPT"},
            headers=AUTH,
        )
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "RESOLVED"
        assert res.json()["resolution"]["action"] == "SET_TYPE"
        queue = deps.task_queue
        assert isinstance(queue, InlineTaskQueue)
        await queue.drain()

        # The fake reader would call it a purchase invoice; the person's choice stands.
        doc = (await client.get(f"/api/documents/{DOC}", headers=AUTH)).json()
        assert doc["docType"] == "RECEIPT" and doc["typeSetBy"] == "u-1"
        assert doc["status"] != "NEEDS_INPUT", doc.get("statusDetail")
        findings = (await client.get("/api/findings", params={"docId": DOC}, headers=AUTH)).json()[
            "items"
        ]
        assert all(f["status"] == "RESOLVED" for f in findings if f["code"].startswith("E03"))
        still_open = (
            await client.get("/api/review-items", params={"status": "OPEN"}, headers=AUTH)
        ).json()["items"]
        assert still_open == []
