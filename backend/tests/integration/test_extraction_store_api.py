"""The extraction store through the API (spec 022, AC-022-1…3): a statement read by the workflow
has its chunks, each linked to the bank lines read from it and with masked text; its pages merge
into one Markdown document; a document whose files and cache are gone gets them back on its first
request and from a rebuild, with no model call; deleting the document removes its chunks.
Synthetic March statement of "Sunrise Coffee Roasters"."""

import io

from httpx import ASGITransport, AsyncClient

from app.adapters.cloud_tasks import InlineTaskQueue
from app.main import create_app
from tests.fakes.bank_line_repository import FakeBankLineRepository
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.document_storage import FakeDocumentStorage
from tests.integration.test_reading_workflow import FIXTURES, _deps

AUTH = {"Authorization": "Bearer owner"}


async def test_ac022_a_read_statement_is_stored_as_chunks_and_rebuilt_without_a_model():
    lines = FakeBankLineRepository()
    deps = _deps(lines, FakeDocumentRepository())
    app = create_app(deps.settings, deps=deps)
    pdf = (FIXTURES / "acb-2026-03.pdf").read_bytes()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/documents",
            headers=AUTH,
            files={"file": ("acb.pdf", io.BytesIO(pdf), "application/pdf")},
        )
        queue = deps.task_queue
        assert isinstance(queue, InlineTaskQueue)
        await queue.drain()
        doc_id = res.json()["docId"]

        chunks = (await client.get(f"/api/documents/{doc_id}/chunks", headers=AUTH)).json()["items"]
        page_two = (
            await client.get(f"/api/documents/{doc_id}/chunks?page=2", headers=AUTH)
        ).json()["items"]
        document = await client.get(f"/api/documents/{doc_id}/extraction.md", headers=AUTH)

        # AC-022-3: a document read before the store: no files, no chunks, no cache.
        storage = deps.storage
        assert isinstance(storage, FakeDocumentStorage)
        storage.extractions.clear()
        storage.cache.clear()
        await deps.chunk_repo.replace_document("org_1", doc_id, [])
        reader_calls = len(getattr(deps.reader, "calls", []))
        first = await client.get(f"/api/documents/{doc_id}/pages/1/extraction.md", headers=AUTH)
        rebuilt = (await client.get(f"/api/documents/{doc_id}/chunks", headers=AUTH)).json()[
            "items"
        ]
        storage.extractions.clear()
        counts = (await client.post("/api/extractions/rebuild", headers=AUTH)).json()

        gone = await client.delete(f"/api/documents/{doc_id}", headers=AUTH)
        after = await deps.chunk_repo.list_chunks("org_1", doc_id)

    stored_lines = {ln.tx_id for ln in await lines.list_lines("org_1", doc_id=doc_id)} or None
    assert chunks and all(
        c["chunkId"].startswith("chk_") and c["source"] == "TEXT_LAYER" for c in chunks
    )
    assert [(c["pageNo"], c["ordinal"]) for c in chunks] == sorted(
        (c["pageNo"], c["ordinal"]) for c in chunks
    )
    assert page_two and {c["pageNo"] for c in page_two} == {2}
    linked = [c for c in chunks if c.get("links", {}).get("txIds")]
    assert linked, "statement rows link the bank lines read from them"
    assert all(c["box"] and 0 <= c["box"]["x0"] < c["box"]["x1"] <= 1 for c in chunks)
    assert (
        document.status_code == 200 and "page 1 of" in document.text and "\n---\n" in document.text
    )
    assert first.status_code == 200 and first.text.startswith("# acb.pdf, page 1 of")
    assert [c["chunkId"] for c in rebuilt] == [c["chunkId"] for c in chunks], (
        "same data, same chunks"
    )
    assert len(getattr(deps.reader, "calls", [])) == reader_calls, "no model call to rebuild"
    assert counts == {"documents": 1, "pages": 2, "withoutText": 0}
    assert gone.status_code == 204 and after == []
    assert stored_lines is None, "the document's lines went with it"


async def test_ac022_6_the_workspace_searches_its_own_chunks():
    from tests.fakes.embedder import FakeEmbedder

    lines = FakeBankLineRepository()
    deps = _deps(lines, FakeDocumentRepository())
    deps._embedder = FakeEmbedder()
    app = create_app(deps.settings, deps=deps)
    pdf = (FIXTURES / "acb-2026-03.pdf").read_bytes()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/documents",
            headers=AUTH,
            files={"file": ("acb.pdf", io.BytesIO(pdf), "application/pdf")},
        )
        queue = deps.task_queue
        assert isinstance(queue, InlineTaskQueue)
        await queue.drain()
        doc_id = res.json()["docId"]
        chunks = (await client.get(f"/api/documents/{doc_id}/chunks", headers=AUTH)).json()["items"]
        target = next(c for c in chunks if "PRIMEPACK" in c["text"])
        found = (
            await client.get(
                "/api/extractions/search", params={"q": "primepack packaging"}, headers=AUTH
            )
        ).json()["items"]
        other = await deps.chunk_repo.nearest("org_other", [1.0] + [0.0] * 767, 5)

    assert found and found[0]["chunkId"] == target["chunkId"] and found[0]["fileName"] == "acb.pdf"
    assert (
        found[0]["pageUrl"] == f"/api/documents/{doc_id}/pages/{found[0]['pageNo']}/extraction.md"
    )
    assert found[0]["similarity"] >= found[-1]["similarity"]
    assert other == [], "another workspace sees nothing"
