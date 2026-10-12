"""Content duplicates end to end (spec 006, AC-006-1, -2, -5): the same statement or invoice in a
re-saved file is held, not counted; with the earlier copy gone, a re-run releases it."""

import io

from app.adapters.cloud_tasks import InlineTaskQueue
from tests.integration.test_integrity_workflow import FIXTURES
from tests.integration.test_invoice_workflow import AUTH, PDF, _client, _deps

STATEMENT = (FIXTURES / "acb-2026-03.pdf").read_bytes()


async def _upload(client, deps, data: bytes, name: str) -> str:
    res = await client.post(
        "/api/documents", headers=AUTH, files={"file": (name, io.BytesIO(data), "application/pdf")}
    )
    assert res.status_code == 201, res.text
    queue = deps.task_queue
    assert isinstance(queue, InlineTaskQueue)
    await queue.drain()
    return res.json()["docId"]


async def test_a_resaved_copy_of_an_invoice_is_held_and_released_when_the_first_is_removed():
    deps, invoices = _deps()
    async with _client(deps) as client:
        first = await _upload(client, deps, PDF.read_bytes(), "invoice.pdf")
        second = await _upload(client, deps, PDF.read_bytes() + b"\n% saved again\n", "copy.pdf")
        doc = (await client.get(f"/api/documents/{second}", headers=AUTH)).json()
        findings = (
            await client.get("/api/findings", params={"docId": second}, headers=AUTH)
        ).json()
        original = (await client.get(f"/api/documents/{first}", headers=AUTH)).json()

        assert doc["heldAsDuplicate"] is True
        assert doc["duplicate"]["kind"] == "CONTENT" and doc["duplicate"]["ofDocId"] == first
        [d03] = [f for f in findings["items"] if f["category"] == "DUPLICATE"]
        assert (d03["code"], d03["severity"], d03["facts"]["held"]) == (
            "D03_INVOICE_DUPLICATE",
            "MEDIUM",
            "yes",
        )
        assert ("org_1", second) in invoices.held and ("org_1", first) not in invoices.held
        assert original["heldAsDuplicate"] is False

        assert (await client.delete(f"/api/documents/{first}", headers=AUTH)).status_code == 204
        queue = deps.task_queue
        assert isinstance(queue, InlineTaskQueue)
        await queue.drain()  # deleting the earlier copy re-reads the held one
        doc = (await client.get(f"/api/documents/{second}", headers=AUTH)).json()
        findings = (
            await client.get("/api/findings", params={"docId": second}, headers=AUTH)
        ).json()

    assert doc["heldAsDuplicate"] is False and doc.get("duplicate") is None
    assert ("org_1", second) not in invoices.held
    assert [f["status"] for f in findings["items"] if f["category"] == "DUPLICATE"] == ["RESOLVED"]


async def test_a_resaved_copy_of_a_statement_is_held_as_the_same_period():
    from httpx import ASGITransport, AsyncClient

    from app.main import create_app
    from tests.fakes.bank_line_repository import FakeBankLineRepository
    from tests.fakes.document_repository import FakeDocumentRepository
    from tests.integration.test_reading_workflow import _deps as statement_deps

    lines = FakeBankLineRepository()
    deps = statement_deps(lines, FakeDocumentRepository())
    app = create_app(deps.settings, deps=deps)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await _upload(client, deps, STATEMENT, "march.pdf")
        second = await _upload(client, deps, STATEMENT + b"\n% saved again\n", "march-copy.pdf")
        doc = (await client.get(f"/api/documents/{second}", headers=AUTH)).json()
        findings = (
            await client.get("/api/findings", params={"docId": second}, headers=AUTH)
        ).json()

    [d02] = [f for f in findings["items"] if f["category"] == "DUPLICATE"]
    assert (d02["code"], d02["severity"]) == ("D02_STATEMENT_PERIOD_DUPLICATE", "MEDIUM")
    assert d02["facts"]["rowsIdentical"] == "yes" and d02["facts"]["overlapDays"] == "31"
    assert doc["heldAsDuplicate"] is True and doc["duplicate"]["ofDocId"] == first
    assert ("org_1", second) in lines.held
