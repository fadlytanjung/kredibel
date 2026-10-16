"""Labels through the API (spec 016, AC-016-5…7): the list and its summary, a person's decision
and what it applies to, a remembered correction, bulk confirmation and who may decide. Synthetic
data only."""

from datetime import UTC, date, datetime
from decimal import Decimal as D

from app.domain.labels import AiDecision, LabelSubject, propose
from app.domain.models.bank_line import BankLine
from tests.fakes.label_repository import FakeLabelRepository
from tests.integration.test_invoice_workflow import AUTH, _client, _deps

ORG = "org_1"
AT = datetime(2026, 7, 2, 9, 14, tzinfo=UTC)


def line(tx: str, amount: str, party: str, day: int) -> BankLine:
    return BankLine(
        tx_id=tx,
        doc_id="doc_may",
        page=1,
        row_index=day,
        date=date(2026, 5, day),
        month="2026-05",
        description=f"TRANSFER OUT {party.upper()}",
        amount=D(amount),
        balance=None,
        counterparty_name=party,
        category="SUPPLIER_PAYMENT",
        categorized_by="MODEL",
        category_confidence=D("0.66"),
    )


async def _seed(deps):
    repo = deps.label_repo
    assert isinstance(repo, FakeLabelRepository)
    await deps.bank_lines.replace_document_lines(
        ORG,
        "doc_may",
        [
            line("tx_1", "-24500000.00", "Roastline Equipment Service", 6),
            line("tx_2", "-1200000.00", "Roastline Equipment Service", 20),
        ],
    )
    ai = AiDecision(
        value="SUPPLIER_PAYMENT",
        source="MODEL",
        at=AT,
        confidence=D("0.66"),
        model="fake-model",
        prompt_version="categorize@test",
        run_id="run_1",
    )
    labels = [
        propose(
            "CATEGORY",
            LabelSubject(
                display="TRANSFER OUT ROASTLINE EQUIPMENT SERVICE",
                doc_id="doc_may",
                page_no=1,
                tx_id="tx_1",
            ),
            ai,
            policy=deps.learning,
            month="2026-05",
            framework="IFRS",
            cashflow_class="OPERATING",
        ),
        propose(
            "DOC_TYPE",
            LabelSubject(display="RES-0045.pdf", doc_id="doc_res", page_no=1),
            AiDecision(
                value="PURCHASE_INVOICE",
                source="MODEL",
                at=AT,
                confidence=D("0.97"),
                run_id="run_2",
            ),
            policy=deps.learning,
        ),
        propose(
            "FIELD_VALUE",
            LabelSubject(display="INV-0024 · total", doc_id="doc_inv", page_no=1, field="total"),
            AiDecision(value="4200000.00", source="MODEL", at=AT, run_id="run_3"),
            policy=deps.learning,
            month="2026-06",
        ),
    ]
    stored = await repo.upsert(ORG, labels)
    return repo, {lb.task: lb for lb in stored}


async def test_ac016_5_6_7_the_list_the_decision_and_the_remembered_correction():
    deps, _ = _deps()
    repo, by_task = await _seed(deps)
    async with _client(deps) as client:
        page = (await client.get("/api/labels", headers=AUTH)).json()
        keys = ("total", "needsCheck", "verified", "corrected", "aiAgreementOnChecked")
        assert {k: page["summary"][k] for k in keys} == {
            "total": 3,
            "needsCheck": 2,
            "verified": 0,
            "corrected": 0,
            "aiAgreementOnChecked": None,
        }
        assert page["summary"]["byTask"]["CATEGORY"] == 1
        assert page["summary"]["byStatus"]["AI_PROPOSED"] == 3
        assert [i["task"] for i in page["items"]] == ["FIELD_VALUE", "CATEGORY", "DOC_TYPE"], (
            "needs a check first, lowest confidence first"
        )
        assert (
            page["items"][1]["ai"]["confidence"] == 0.66 and page["items"][1]["needsCheck"] is True
        )
        assert page["items"][1]["pageImageUrl"] is None and page["items"][1]["dataset"] == {
            "use": "EXCLUDED",
            "reason": "not checked by a person",
        }
        only = (await client.get("/api/labels?task=CATEGORY&needsCheck=true", headers=AUTH)).json()
        assert [i["labelId"] for i in only["items"]] == [by_task["CATEGORY"].label_id]

        # A correction with "apply to similar lines": the line, the months and a rule follow.
        res = await client.post(
            f"/api/labels/{by_task['CATEGORY'].label_id}/decision",
            headers=AUTH,
            json={
                "action": "CORRECT",
                "value": "INVENTORY_PURCHASE",
                "note": "beans",
                "applyToSimilar": True,
            },
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["status"] == "CORRECTED" and body["final"] == {
            "value": "INVENTORY_PURCHASE",
            "source": "PERSON",
        }
        assert (
            body["decidedBy"] == "u-1"
            and body["note"] == "beans"
            and body["dataset"]["use"] in ("TRAIN", "EVAL")
        )
        changed = await deps.bank_lines.get_line(ORG, "tx_1")
        assert (
            changed is not None
            and changed.category == "INVENTORY_PURCHASE"
            and changed.categorized_by == "USER"
        )
        rules = await repo.list_rules(ORG)
        assert (
            len(rules) == 1
            and rules[0].category == "INVENTORY_PURCHASE"
            and rules[0].direction == "out"
        )
        assert (
            repo.events[-1].type == "LABEL_CORRECTED"
            and repo.events[-1].details["aiValue"] == "SUPPLIER_PAYMENT"
        )

        bad = await client.post(
            f"/api/labels/{by_task['CATEGORY'].label_id}/decision",
            headers=AUTH,
            json={"action": "CORRECT", "value": "NOT_A_CATEGORY"},
        )
        assert bad.status_code == 422

        # Bulk confirmation takes the AI's values; an already decided label is left alone.
        res = await client.post(
            "/api/labels/bulk-confirm",
            headers=AUTH,
            json={"labelIds": [lb.label_id for lb in by_task.values()]},
        )
        assert res.status_code == 200 and res.json() == {"updated": 2}
        page = (await client.get("/api/labels?sort=newest", headers=AUTH)).json()
        assert page["summary"]["verified"] == 2 and page["summary"]["corrected"] == 1
        assert (
            page["summary"]["aiAgreementOnChecked"] == 0.6667 and page["summary"]["needsCheck"] == 0
        )
        one = (await client.get(f"/api/labels/{by_task['DOC_TYPE'].label_id}", headers=AUTH)).json()
        assert one["status"] == "VERIFIED" and one["final"]["value"] == "PURCHASE_INVOICE"

        # A later run proposes something else: the person's value stands and the disagreement shows.
        again = propose(
            "CATEGORY",
            LabelSubject(display="x", doc_id="doc_may", page_no=1, tx_id="tx_1"),
            AiDecision(value="RENT", source="MODEL", at=AT, confidence=D("0.9"), run_id="run_9"),
            policy=deps.learning,
            month="2026-05",
        )
        [stored] = await repo.upsert(ORG, [again])
        assert (
            stored.final_value == "INVENTORY_PURCHASE"
            and stored.ai_disagrees_with_person
            and stored.ai.run_id == "run_9"
        )

        missing = await client.get("/api/labels/lbl_0000000000000000", headers=AUTH)
        assert missing.status_code == 404


async def test_ac013_18_a_viewer_reads_labels_but_cannot_decide():
    deps, _ = _deps()
    from tests.unit.test_auth import FakeTokenVerifier

    deps._token_verifier = FakeTokenVerifier(
        {
            "owner": {"uid": "u-1", "orgId": ORG, "role": "owner"},
            "viewer": {"uid": "u-9", "orgId": ORG, "role": "viewer"},
        }
    )
    _, by_task = await _seed(deps)
    async with _client(deps) as client:
        seen = await client.get("/api/labels", headers={"Authorization": "Bearer viewer"})
        assert seen.status_code == 200 and seen.json()["summary"]["total"] == 3
        denied = await client.post(
            f"/api/labels/{by_task['CATEGORY'].label_id}/decision",
            headers={"Authorization": "Bearer viewer"},
            json={"action": "CONFIRM"},
        )
        assert denied.status_code == 403
        denied = await client.post(
            "/api/labels/bulk-confirm",
            headers={"Authorization": "Bearer viewer"},
            json={"labelIds": [by_task["CATEGORY"].label_id]},
        )
        assert denied.status_code == 403


async def test_ac016_1_labels_for_books_read_before_labels_existed_and_safe_to_repeat():
    from app.domain.models.document import DocStatus, DocType, Document

    deps, _ = _deps()
    await deps.doc_repo.save_document(
        ORG,
        Document(
            doc_id="doc_may",
            file_name="ACB_May_2026.pdf",
            content_type="application/pdf",
            size_bytes=1,
            page_count=1,
            sha256="b" * 64,
            gcs_path="gs://synthetic/doc_may.pdf",
            uploaded_by="u-1",
            uploaded_at=AT,
            doc_type=DocType.BANK_STATEMENT,
            type_confidence=D("0.99"),
            status=DocStatus.DONE,
            months=["2026-05"],
        ),
    )
    await deps.bank_lines.replace_document_lines(
        ORG,
        "doc_may",
        [
            line("tx_1", "-24500000.00", "Roastline Equipment Service", 6),
            line("tx_2", "-1200000.00", "Roastline Equipment Service", 20),
        ],
    )
    async with _client(deps) as client:
        assert (await client.get("/api/labels", headers=AUTH)).json()["summary"]["total"] == 0
        res = await client.post("/api/labels/sync", headers=AUTH)
        assert res.status_code == 200 and res.json() == {"created": 3}
        page = (await client.get("/api/labels", headers=AUTH)).json()
        assert (
            page["summary"]["byTask"]["CATEGORY"] == 2
            and page["summary"]["byTask"]["DOC_TYPE"] == 1
        )
        # Even a 0.99 decision is a label a person can still correct.
        doc_label = next(i for i in page["items"] if i["task"] == "DOC_TYPE")
        assert doc_label["ai"]["confidence"] == 0.99 and doc_label["status"] == "AI_PROPOSED"
        again = await client.post("/api/labels/sync", headers=AUTH)
        assert again.json() == {"created": 0}, "nothing new, nothing written"


async def test_ac016_6_a_category_set_on_the_month_page_is_the_person_s_correction():
    deps, _ = _deps()
    repo, by_task = await _seed(deps)
    async with _client(deps) as client:
        res = await client.patch(
            "/api/bank-lines/tx_1", headers=AUTH, json={"category": "INVENTORY_PURCHASE"}
        )
        assert res.status_code == 200, res.text
    label = await repo.get(ORG, by_task["CATEGORY"].label_id)
    assert label is not None and label.status == "CORRECTED"
    assert label.final_value == "INVENTORY_PURCHASE" and label.ai.value == "SUPPLIER_PAYMENT"
    assert label.decided_by == "u-1" and repo.events[-1].type == "LABEL_CORRECTED"
