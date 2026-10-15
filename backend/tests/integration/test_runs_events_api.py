"""A run's events and the labels it produced (spec 017, AC-017-5…7): stages become events with
latency, tokens and spans; label counts ride on the run; only the owner sees events."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

from app.domain.labels import AiDecision, LabelSubject, propose
from app.domain.models.run import Run, RunKind, RunStage, RunStatus, StageStatus
from tests.integration.test_invoice_workflow import AUTH, _client, _deps

ORG = "org_1"
T0 = datetime(2026, 7, 2, 9, 14, tzinfo=UTC)


async def _seed(deps) -> str:
    run_id = "doc-doc_mar-1"
    run = Run(
        run_id=run_id,
        kind=RunKind.DOCUMENT,
        target="doc_mar",
        status=RunStatus.DONE,
        trace_id="4be0" * 8,
        models=["fake-model"],
        prompt_versions={"classify": "classify@test"},
        created_at=T0,
        ended_at=T0 + timedelta(seconds=41),
    )
    await deps.run_repo.create(ORG, run)
    stages = [
        RunStage(
            node="inspect_file",
            status=StageStatus.DONE,
            started_at=T0,
            ended_at=T0 + timedelta(seconds=1),
            summary="2 save(s)",
            trace_span_id="a1",
        ),
        RunStage(
            node="classify_document",
            status=StageStatus.DONE,
            started_at=T0 + timedelta(seconds=1),
            ended_at=T0 + timedelta(seconds=3),
            model="fake-model",
            tokens_in=2100,
            tokens_out=100,
            summary="BANK_STATEMENT (0.99)",
            trace_span_id="b2",
        ),
        RunStage(
            node="read_page",
            parent="read_pages",
            status=StageStatus.DONE,
            started_at=T0 + timedelta(seconds=3),
            ended_at=T0 + timedelta(seconds=12),
            model="fake-model",
            tokens_in=3400,
            tokens_out=900,
            summary="page 1",
            trace_span_id="c3",
        ),
    ]
    for stage in stages:
        await deps.run_repo.append_stage(ORG, run_id, stage)
    label = propose(
        "DOC_TYPE",
        LabelSubject(display="ACB_Mar_2026.pdf", doc_id="doc_mar", page_no=1),
        AiDecision(
            value="BANK_STATEMENT",
            source="MODEL",
            at=T0,
            confidence=D("0.99"),
            model="fake-model",
            prompt_version="classify@test",
            run_id=run_id,
        ),
        policy=deps.learning,
    )
    await deps.label_repo.upsert(ORG, [label])
    return run_id


async def test_ac017_5_6_7_a_run_lists_its_labels_and_its_events_in_time_order():
    deps, _ = _deps()
    run_id = await _seed(deps)
    async with _client(deps) as client:
        run = (await client.get(f"/api/runs/{run_id}", headers=AUTH)).json()
        assert run["labels"] == {"proposed": 1, "verified": 0, "corrected": 0}
        assert run["traceUrl"].endswith(run["traceId"]) and run["models"] == ["fake-model"]
        listed = (await client.get("/api/runs", headers=AUTH)).json()["items"]
        assert [r["runId"] for r in listed] == [run_id] and listed[0]["labels"]["proposed"] == 1

        events = (await client.get(f"/api/runs/{run_id}/events", headers=AUTH)).json()
        assert events["contentCaptured"] is False
        kinds = [(e["node"], e["eventType"]) for e in events["items"]]
        assert kinds == [
            ("inspect_file", "NODE_OUTPUT"),
            ("classify_document", "NODE_OUTPUT"),
            ("classify_document", "LLM_RESPONSE"),
            ("read_page", "NODE_OUTPUT"),
            ("read_page", "LLM_RESPONSE"),
        ]
        llm = events["items"][2]
        assert llm["model"] == "fake-model" and (llm["tokensIn"], llm["tokensOut"]) == (2100, 100)
        assert llm["latencyMs"] == 2000 and llm["spanId"] == "b2" and llm["content"] is None
        assert len(llm["labelIds"]) == 1 and events["items"][0]["labelIds"] == []
        assert events["items"][3]["parentSpanId"] == "read_pages"

        missing = await client.get("/api/runs/run_nope/events", headers=AUTH)
        assert missing.status_code == 404


async def test_ac013_18_only_the_owner_sees_agent_events():
    from tests.unit.test_auth import FakeTokenVerifier

    deps, _ = _deps()
    deps._token_verifier = FakeTokenVerifier(
        {
            "owner": {"uid": "u-1", "orgId": ORG, "role": "owner"},
            "reviewer": {"uid": "u-5", "orgId": ORG, "role": "reviewer"},
        }
    )
    run_id = await _seed(deps)
    async with _client(deps) as client:
        denied = await client.get(
            f"/api/runs/{run_id}/events", headers={"Authorization": "Bearer reviewer"}
        )
        assert denied.status_code == 403
        allowed = await client.get(
            f"/api/runs/{run_id}", headers={"Authorization": "Bearer reviewer"}
        )
        assert allowed.status_code == 200
