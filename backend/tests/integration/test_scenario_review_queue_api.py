"""The review queue on S1 and S3 through the API (spec 009, T009-07; AC-009-8, AC-009-9).

The scenario's books are seeded as the document workflow leaves them (`scenario_books`); the month
runs, the queue and every resolution go through the API the app uses. Synthetic data only.
Where the policy decides differently from `truth.json`, the policy wins and the test says so.
"""

from tests.integration import scenario_books as books
from tests.integration.test_invoice_workflow import AUTH, _client


async def _queue(client) -> list[dict]:
    res = await client.get(
        "/api/review-items", params={"status": "OPEN", "limit": 500}, headers=AUTH
    )
    assert res.status_code == 200, res.text
    return res.json()["items"]


async def _states(client) -> dict[str, str]:
    out = {}
    for month in books.MONTHS:
        res = await client.get(f"/api/months/{month}", headers=AUTH)
        assert res.status_code == 200, res.text
        out[month] = res.json()["state"]
    return out


async def _open_findings(client, month: str) -> list[tuple[str, str]]:
    res = await client.get("/api/findings", params={"month": month, "limit": 200}, headers=AUTH)
    assert res.status_code == 200, res.text
    return sorted((f["code"], f["severity"]) for f in res.json()["items"] if f["status"] == "OPEN")


async def _resolve(client, item: dict, action: str, **body) -> None:
    res = await client.post(
        f"/api/review-items/{item['itemId']}/resolve",
        json={"action": action, **body},
        headers=AUTH,
    )
    assert res.status_code == 200, res.text


async def test_ac009_8_s1_queue_holds_only_what_the_truth_expects_and_resolving_reconciles():
    truth = books.load_truth("S1")
    deps = books.books_deps()
    async with _client(deps) as client:
        await books.seed(deps, "S1", truth)
        await books.run_months(deps)
        items = await _queue(client)
        by_kind: dict[str, list[dict]] = {}
        for item in items:
            by_kind.setdefault(item["kind"], []).append(item)
        # Documents paid in a later month are not asked about (the payment's run re-ran theirs),
        # cash receipts are paid in cash, and the not-yet-due June invoice waits for July.
        assert set(by_kind) == {"PROPOSED_MATCH", "UNMATCHED_BANK_LINE"}, {
            k: [i["title"] for i in v] for k, v in by_kind.items()
        }

        # The ambiguous February pair is proposed, never automatic (truth.json).
        proposals = by_kind["PROPOSED_MATCH"]
        [feb] = [i for i in proposals if i["month"] == "2026-02"]
        assert feb["subject"]["bankLineIds"] == ["st-02#8"]
        # The proposal first, then the rivals code scored for the same records (spec 023, AC-023-7).
        proposal, *rivals = feb["suggestion"]["candidates"]
        assert proposal["matchId"] == feb["subject"]["matchId"]
        mine = {*proposal["bankLineIds"], *proposal["invoiceIds"], *proposal["receiptIds"]}
        for rival in rivals:
            assert mine & {*rival["bankLineIds"], *rival["invoiceIds"], *rival["receiptIds"]}
        assert all(c["aiRank"] for c in feb["suggestion"]["candidates"]) or not rivals
        assert feb["allowedActions"] == ["CONFIRM_MATCH", "MATCH", "REJECT_MATCH"]
        # A payment net of withholding tax is a proposal until a person confirms the adjustment
        # (reconciliation.v1 netOfTaxAmountScore); truth.json marks this one automatic.
        [mar] = [i for i in proposals if i["month"] == "2026-03"]
        assert "NET_OF_TAX" in mar["suggestion"]["candidates"][0]["reasons"]
        assert len(proposals) == 2

        # The June cash deposit missing from the ledger: X09 names it, so the queue asks.
        [deposit] = by_kind["UNMATCHED_BANK_LINE"]
        assert (deposit["month"], deposit["subject"]["bankLineIds"]) == ("2026-06", ["st-06#22"])
        assert "no supporting document" in deposit["title"]

        for month, expected in books.expected_items(truth).items():
            counted = books.count_items([i for i in items if i["month"] == month])[month]
            assert all(counted.get(kind, 0) >= n for kind, n in expected.items()), (month, counted)

        before = await _states(client)
        assert before["2026-02"] == "NEEDS_REVIEW" and before["2026-03"] == "NEEDS_REVIEW"
        assert before["2026-06"] == "NEEDS_REVIEW"
        assert before["2026-01"] == before["2026-04"] == before["2026-05"] == "RECONCILED"
        june = await _open_findings(client, "2026-06")
        assert june == [("X09_LEDGER_BANK_MISMATCH", "HIGH")], june  # 2.1M of a 5.4M movement

        # A person resolves them; each resolution re-runs its month.
        for item in proposals:
            await _resolve(client, item, "CONFIRM_MATCH")
        await _resolve(
            client, deposit, "NO_DOCUMENT_NEEDED", reason="Cash sales banked; nothing to attach."
        )
        await books.drain(deps)

        assert await _queue(client) == []
        after = await _states(client)
        # June keeps its blocking ledger difference until the ledger is corrected (spec 007).
        assert after == {**dict.fromkeys(books.MONTHS, "RECONCILED"), "2026-06": "NEEDS_REVIEW"}
        assert await _open_findings(client, "2026-06") == [("X09_LEDGER_BANK_MISMATCH", "HIGH")]


def _values(figures: dict) -> dict[str, str]:
    return {name: body["value"] for name, body in figures.items()}


async def _figures(client) -> dict[str, dict[str, str]]:
    out = {}
    for month in books.MONTHS:
        res = await client.get(f"/api/months/{month}", headers=AUTH)
        assert res.status_code == 200, res.text
        out[month] = _values(res.json()["figures"])
    return out


async def _s1_figures() -> dict[str, dict[str, str]]:
    deps = books.books_deps()
    async with _client(deps) as client:
        await books.seed(deps, "S1", books.load_truth("S1"))
        await books.run_months(deps)
        return await _figures(client)


def _copies(truth: dict) -> dict[str, dict]:
    """The held copies by their document id, with the original's entry."""
    originals = {d["file"]: d for d in truth["documents"] if "copyOf" not in d}
    return {
        books.doc_id_of(d["key"]): {**d, "original": originals[d["copyOf"]]}
        for d in truth["documents"]
        if "copyOf" in d and d["expected"]["duplicate"]["held"]
    }


async def test_ac009_9_s3_held_copies_keep_the_figures_equal_to_s1_until_one_is_released():
    """S3's four copies: three documents (D02, D03, D05) and a journal entry entered twice in the
    ledger (D06). The exact copy (D01) is refused at upload and never read, so it gets no item."""
    import io

    s1_figures = await _s1_figures()
    truth = books.load_truth("S3")
    copies = _copies(truth)
    deps = books.books_deps()
    async with _client(deps) as client:
        await books.seed(deps, "S3", truth, copies=True)
        exact = next(
            d
            for d in truth["documents"]
            if "copyOf" in d and d["expected"]["duplicate"]["code"].startswith("D01")
        )
        res = await client.post(
            "/api/documents",
            files={
                "file": (
                    exact["file"],
                    io.BytesIO(books.scenario_file("S3", exact["file"]).read_bytes()),
                    "application/pdf",
                )
            },
            headers=AUTH,
        )
        assert res.status_code == 201, res.text
        body = res.json()
        original = next(d for d in truth["documents"] if d.get("file") == exact["copyOf"])
        assert (
            body["status"] == "DUPLICATE"
            and body["duplicate"]["code"] == exact["expected"]["duplicate"]["code"]
        )
        assert body["duplicate"]["ofDocId"] == books.doc_id_of(original["key"])
        await books.drain(deps)

        await books.run_months(deps)
        items = await _queue(client)
        held = [i for i in items if i["kind"] == "POSSIBLE_DUPLICATE"]
        ledger = next(d for d in truth["documents"] if d.get("docType") == "LEDGER_EXPORT")
        ledger_month = next(
            e["date"][:7] for e in ledger["entries"] if e["key"] in ledger["duplicateEntries"]
        )

        def first_month(original: dict) -> str:
            when = original.get("period", {}).get("start") or original.get("issueDate") or ""
            return (when or original.get("issuedAt", ""))[:7]

        expected_held = sorted(
            [(first_month(c["original"]), doc_id) for doc_id, c in copies.items()]
            + [(ledger_month, books.doc_id_of(ledger["key"]))]
        )
        assert sorted((i["month"], i["docId"]) for i in held) == expected_held
        for item in held:
            assert item["allowedActions"] == ["CONFIRM_DUPLICATE", "NOT_DUPLICATE"]
            if item["subject"]["ledgerEntryIds"]:
                assert len(item["subject"]["ledgerEntryIds"]) == len(ledger["duplicateEntries"])
                assert "appears twice" in item["title"]
                continue
            assert item["subject"]["docIds"] == [
                item["docId"],
                books.doc_id_of(copies[item["docId"]]["original"]["key"]),
            ]
        assert [
            i
            for i in items
            if i["kind"] not in ("POSSIBLE_DUPLICATE", "PROPOSED_MATCH", "UNMATCHED_BANK_LINE")
        ] == []
        assert await _figures(client) == s1_figures, (
            "nothing is counted twice while copies are held"
        )

        # Confirming the copies keeps them out for good; the figures do not move.
        for item in held:
            await _resolve(client, item, "CONFIRM_DUPLICATE")
        await books.drain(deps)
        assert [i for i in await _queue(client) if i["kind"] == "POSSIBLE_DUPLICATE"] == []
        assert await _figures(client) == s1_figures

    # Rejecting one adds its values back: the February re-export counts as a second statement.
    deps = books.books_deps()
    async with _client(deps) as client:
        await books.seed(deps, "S3", truth, copies=True)
        await books.run_months(deps)
        [statement_copy] = [
            i
            for i in await _queue(client)
            if i["kind"] == "POSSIBLE_DUPLICATE"
            and i["docId"] in copies
            and copies[i["docId"]]["expected"]["duplicate"]["code"].startswith("D02")
        ]
        await _resolve(client, statement_copy, "NOT_DUPLICATE")
        await books.drain(deps)
        released = await _figures(client)
        from decimal import Decimal

        for name in ("moneyIn", "moneyOut"):
            assert Decimal(released["2026-02"][name]) == 2 * Decimal(s1_figures["2026-02"][name])
        for month in books.MONTHS:
            if month != "2026-02":
                assert released[month] == s1_figures[month], month
