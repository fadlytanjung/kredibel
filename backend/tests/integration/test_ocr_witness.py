"""The OCR witness (spec 022 phase B, AC-022-4): a receipt photo has no text layer, so its page
image is read by OCR; the words become the page's chunks, the reading is checked against them
(AI_OCR, values agreed instead of single-source), the chunks are stored with source OCR, and a
second read of the same image uses the OCR cache. Synthetic receipt of "Sunrise Coffee Roasters"."""

import io

import pypdfium2 as pdfium
from httpx import ASGITransport, AsyncClient

from app.adapters.cloud_tasks import InlineTaskQueue
from app.adapters.text_layer import PdfTextLayer
from app.main import create_app
from tests.fakes.ocr_text import FakeOcr
from tests.support.reconciliation_demo import FIXTURES, demo_deps

AUTH = {"Authorization": "Bearer owner"}


def photo_and_words() -> tuple[bytes, FakeOcr]:
    pdf = (FIXTURES / "receipt-2026-03-01.pdf").read_bytes()
    png = io.BytesIO()
    pdfium.PdfDocument(pdf)[0].render(scale=2).to_pil().save(png, format="PNG")
    words = PdfTextLayer().words(pdf)[1]
    return png.getvalue(), FakeOcr(words)


async def test_ac022_4_a_receipt_photo_is_read_twice_with_ocr():
    image, ocr = photo_and_words()
    deps = demo_deps()
    deps._ocr = ocr
    app = create_app(deps.settings, deps=deps)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/documents",
            headers=AUTH,
            files={"file": ("receipt photo.png", io.BytesIO(image), "image/png")},
        )
        assert res.status_code == 201, res.text
        queue = deps.task_queue
        assert isinstance(queue, InlineTaskQueue)
        await queue.drain()
        doc_id = res.json()["docId"]
        doc = (await client.get(f"/api/documents/{doc_id}", headers=AUTH)).json()
        chunks = (await client.get(f"/api/documents/{doc_id}/chunks", headers=AUTH)).json()["items"]
        page = await client.get(f"/api/documents/{doc_id}/pages/1/extraction.md", headers=AUTH)
        # AC-022-5: reading it again uses the OCR cache: the image is not sent twice.
        again = await client.post(f"/api/documents/{doc_id}/reread", headers=AUTH)
        await queue.drain()
        after = (await client.get(f"/api/documents/{doc_id}", headers=AUTH)).json()

    receipts = await deps.receipts.list_records("org_1", doc_id=doc_id)
    total = receipts[0].consensus.get("total") or {}
    assert doc["docType"] == "RECEIPT" and doc["reading"]["method"] == "AI_OCR"
    assert doc["pages"][0]["witness"] == "OCR"
    assert ocr.calls == 1
    assert chunks and {c["source"] for c in chunks} == {"OCR"}
    assert total.get("status") == "AGREED", "the photo's total is checked against the OCR words"
    assert "Reading: AI_OCR" in page.text
    assert again.status_code == 202 and again.json()["runId"] == f"doc-{doc_id}-2"
    assert after["reading"]["method"] == "AI_OCR" and ocr.calls == 1
