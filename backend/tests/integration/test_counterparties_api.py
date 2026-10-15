"""Clients and suppliers, and profile suggestions, through the API (spec 014, T014-03, T014-05;
AC-014-2…7). S1's books are seeded as the document workflow leaves them (`scenario_books`), the
month runs build the picture, and every read and decision goes through the API. Synthetic only."""

import unicodedata

from app.domain.accounts import mask_tax_id
from tests.fakes.document_reader import FakeDocumentReader
from tests.integration import scenario_books as books
from tests.integration.test_invoice_workflow import AUTH, _client, _deps
from tests.integration.test_month_workflow_reconcile import STATEMENT, _classify, _upload
from tests.integration.test_reading_workflow import _recorded_page


def _plain(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text)
    return " ".join("".join(c for c in folded if not unicodedata.combining(c)).casefold().split())


async def _parties(client, **params) -> list[dict]:
    res = await client.get("/api/counterparties", params={"limit": 500, **params}, headers=AUTH)
    assert res.status_code == 200, res.text
    return res.json()["items"]


async def test_ac014_3_s1_counterparties_equal_the_truth_with_one_account_each():
    truth = books.load_truth("S1")
    deps = books.books_deps()
    async with _client(deps) as client:
        await books.seed(deps, "S1", truth)
        await books.run_months(deps)
        parties = await _parties(client)
        by_name = {_plain(p["name"]): p for p in parties}
        for expected in truth["expectedCounterparties"]:
            key = _plain(expected["name"])
            if expected["roles"] == ["GOVERNMENT"]:
                # Unnamed tax rows go to the policy's bucket, worded by categories.v1.yaml.
                [bucket] = [p for p in parties if p["roles"] == ["GOVERNMENT"]]
                assert bucket["bucket"] is True and bucket["kind"] == "GOVERNMENT"
                continue
            assert key in by_name, (expected, sorted(by_name))
            party = by_name[key]
            assert party["roles"] == expected["roles"], party["name"]
            assert len(party["accountsSeen"]) == expected.get("accountsSeen", 0)
            assert party["counterpartyId"].startswith("cp_") and party["bucket"] is False
        # Every bank line of a client is reachable from it, and so are its invoices.
        daybreak = by_name[_plain("DAYBREAK CAFÉ")]
        assert daybreak["kind"] == "BUSINESS" and daybreak["totalIn"]["amount"] > "0"
        lines = (
            await client.get(
                "/api/bank-lines",
                params={"counterpartyId": daybreak["counterpartyId"]},
                headers=AUTH,
            )
        ).json()["items"]
        assert lines and all(ln["counterpartyId"] == daybreak["counterpartyId"] for ln in lines)
        invoices = (
            await client.get(
                "/api/invoices", params={"counterpartyId": daybreak["counterpartyId"]}, headers=AUTH
            )
        ).json()["items"]
        assert invoices and all(i["kind"] == "SALES" for i in invoices)
        one = (
            await client.get(f"/api/counterparties/{daybreak['counterpartyId']}", headers=AUTH)
        ).json()
        assert one["name"] == daybreak["name"] and set(one["totalsByMonth"]) <= set(books.MONTHS)
        suppliers = await _parties(client, role="SUPPLIER")
        assert suppliers and all("SUPPLIER" in p["roles"] for p in suppliers)
        found = await _parties(client, q="daybreak")
        assert [p["counterpartyId"] for p in found] == [daybreak["counterpartyId"]]
        missing = await client.get("/api/counterparties/cp_0000000000000000", headers=AUTH)
        assert missing.status_code == 404


async def test_ac014_3_s4_a_supplier_paid_to_two_accounts_shows_both():
    truth = books.load_truth("S4")
    deps = books.books_deps()
    async with _client(deps) as client:
        await books.seed(deps, "S4", truth)
        await books.run_months(deps)
        [roastline] = [
            p
            for p in await _parties(client)
            if _plain(p["name"]) == _plain("Roastline Equipment Service")
        ]
    [expected] = [c for c in truth["expectedCounterparties"] if "ROASTLINE" in c["name"]]
    assert expected["accountsSeen"] == 2
    accounts = roastline["accountsSeen"]
    assert len(accounts) == 2 and accounts[0]["firstSeen"] <= accounts[1]["firstSeen"]
    assert {a["accountMasked"] for a in accounts} == {"••••3318", "••••3108"}


async def test_ac014_7_s1_suggestions_equal_the_truth_and_a_person_decides_them():
    truth = books.load_truth("S1")
    deps = books.books_deps()
    async with _client(deps) as client:
        await books.seed(deps, "S1", truth)
        await books.run_months(deps)
        items = (await client.get("/api/suggestions", headers=AUTH)).json()["items"]
        by_field = {s["field"]: s for s in items}
        expected = {s["field"]: s for s in truth["expectedSuggestions"]}
        assert set(by_field) == set(expected) == {"TAX_ID", "ADDRESS"}
        tax, address = by_field["TAX_ID"], by_field["ADDRESS"]
        assert tax["display"] == mask_tax_id(expected["TAX_ID"]["value"]["taxId"])
        assert tax["confidence"] == expected["TAX_ID"]["confidence"] == "HIGH"
        assert tax["status"] == "PENDING" and len(tax["evidence"]) >= 2
        assert address["value"] == expected["ADDRESS"]["value"]
        assert address["confidence"] == expected["ADDRESS"]["confidence"] == "MEDIUM"

        # Accepting writes the value into the profile and is recorded; a second decision is refused.
        res = await client.patch(
            f"/api/suggestions/{tax['suggestionId']}", json={"decision": "ACCEPT"}, headers=AUTH
        )
        assert res.status_code == 200 and res.json()["status"] == "ACCEPTED", res.text
        profile = (await client.get("/api/workspace", headers=AUTH)).json()["profile"]
        assert profile["taxIdMasked"] == tax["display"]
        again = await client.patch(
            f"/api/suggestions/{tax['suggestionId']}", json={"decision": "REJECT"}, headers=AUTH
        )
        assert again.status_code == 409 and again.json()["code"] == "SUGGESTION_ALREADY_DECIDED"

        # Rejecting keeps the value out of the profile and off the open suggestions, for good.
        res = await client.patch(
            f"/api/suggestions/{address['suggestionId']}", json={"decision": "REJECT"}, headers=AUTH
        )
        assert res.status_code == 200 and res.json()["status"] == "REJECTED"
        await books.run_months(deps, ["2026-06"])
        open_items = (
            await client.get("/api/suggestions", params={"status": "PENDING"}, headers=AUTH)
        ).json()["items"]
        assert open_items == []
        profile = (await client.get("/api/workspace", headers=AUTH)).json()["profile"]
        assert "address" not in profile
    events = deps.workspace_repo.events.get("org_1", [])  # type: ignore[attr-defined]
    kinds = [e.type for e in deps.suggestion_repo.events]  # type: ignore[attr-defined]
    assert kinds == ["SUGGESTION_ACCEPTED", "SUGGESTION_REJECTED"]
    assert any(e.type == "PROFILE_UPDATED" for e in events)


async def test_ac014_4_an_undeclared_statement_account_is_suggested_and_accepting_declares_it():
    deps, _ = _deps()
    deps._reader = FakeDocumentReader(_classify, pages=_recorded_page)
    async with _client(deps) as client:
        await _upload(client, deps, STATEMENT, "march.pdf")
        [bank] = (await client.get("/api/suggestions", headers=AUTH)).json()["items"]
        assert bank["field"] == "BANK_ACCOUNT" and bank["status"] == "PENDING"
        assert bank["value"]["accountMasked"] == "••••4821"
        assert bank["value"]["bankName"] == "Archipelago Commerce Bank"
        assert bank["confidence"] == "HIGH", "every header value agreed with the text layer"
        assert "accountHash" not in bank["value"], "the hash never leaves orgPrivate"
        res = await client.patch(
            f"/api/suggestions/{bank['suggestionId']}", json={"decision": "ACCEPT"}, headers=AUTH
        )
        assert res.status_code == 200, res.text
        accounts = (await client.get("/api/bank-accounts", headers=AUTH)).json()
        listed = accounts["items"] if isinstance(accounts, dict) else accounts
        [account] = listed
        assert account["accountMasked"] == "••••4821" and account["source"] == "DETECTED"
    hashes = deps.workspace_repo.account_hashes.get("org_1", {})  # type: ignore[attr-defined]
    assert list(hashes.values()) and all(len(h) == 64 for h in hashes.values())
