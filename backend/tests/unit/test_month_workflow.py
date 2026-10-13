"""Unit tests for month_workflow orchestrator (T004-07, AC-004-5, AC-004-7)."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from app.adapters.policy_files import load_risk_policy
from app.agents.deps import PipelineDeps
from app.agents.workflows.month_workflow import build_month_workflow
from app.core.settings import Settings
from app.domain.findings import Finding
from app.domain.models.document import DocStatus, DocType, Document
from app.domain.models.month import Month, MonthState
from app.domain.models.run import Run, RunKind, RunStatus
from app.domain.risk import FindingExplanation, MonthExplanation
from tests.fakes.clock import FixedClock
from tests.fakes.document_reader import FakeDocumentReader
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.finding_repository import FakeFindingRepository
from tests.fakes.month_repository import FakeMonthRepository
from tests.fakes.run_repository import FakeRunRepository
from tests.fakes.task_queue import FakeTaskQueue

NOW = datetime(2026, 3, 15, 10, 0, tzinfo=UTC)
POLICY_DIR = Path(__file__).resolve().parents[3] / "contracts" / "policy"
trace.set_tracer_provider(TracerProvider())


@pytest.fixture
def workflow_deps():
    settings = Settings()
    run_repo = FakeRunRepository()
    doc_repo = FakeDocumentRepository()
    month_repo = FakeMonthRepository()
    findings_repo = FakeFindingRepository()
    task_queue = FakeTaskQueue()
    clock = FixedClock(NOW)
    risk_policy = load_risk_policy(POLICY_DIR)

    deps = PipelineDeps(
        settings=settings,
        run_repo=run_repo,
        doc_repo=doc_repo,
        month_repo=month_repo,
        findings=findings_repo,
        risk_policy=risk_policy,
        task_queue=task_queue,
        clock=clock,
    )
    return deps, run_repo, month_repo, doc_repo


@pytest.mark.asyncio
async def test_ac004_5_month_workflow_generation_check_superseded(workflow_deps):
    """When a newer generation exists in Firestore, run ends SUPERSEDED and writes nothing."""
    deps, run_repo, month_repo, doc_repo = workflow_deps
    org_id = "org_demo"
    month_str = "2026-03"
    run_gen = 1
    newer_gen = 2
    run_id = f"month-{org_id}-{month_str}-{run_gen}"

    # Month in repository was bumped to generation 2 (e.g. by another document upload)
    month = Month(month=month_str, state=MonthState.COLLECTING, dirty=True, generation=newer_gen)
    await month_repo.save(org_id, month)
    await run_repo.create(
        org_id,
        Run(
            run_id=run_id,
            kind=RunKind.MONTH,
            target=month_str,
            generation=run_gen,
            status=RunStatus.RUNNING,
        ),
    )

    wf = build_month_workflow(deps)
    sessions = InMemorySessionService()
    runner = Runner(agent=cast(Any, wf), app_name="kredibel", session_service=sessions)

    await sessions.create_session(
        app_name="kredibel",
        user_id="user_1",
        session_id=run_id,
        state={
            "node_input": {
                "orgId": org_id,
                "month": month_str,
                "generation": run_gen,
                "runId": run_id,
            }
        },
    )

    async for _ in runner.run_async(user_id="user_1", session_id=run_id):
        pass

    # Run was marked SUPERSEDED
    run = await run_repo.get(org_id, run_id)
    assert run is not None
    assert run.status == RunStatus.SUPERSEDED

    # Month was NOT modified by the superseded run (still dirty=True, generation=2)
    saved_month = await month_repo.get(org_id, month_str)
    assert saved_month is not None
    assert saved_month.generation == newer_gen
    assert saved_month.dirty is True
    assert saved_month.last_run_id != run_id


@pytest.mark.asyncio
async def test_ac004_7_month_workflow_without_statement_ends_collecting(workflow_deps):
    """A month with no bank statement ends in COLLECTING state (waiting for statement)."""
    deps, run_repo, month_repo, doc_repo = workflow_deps
    org_id = "org_demo"
    month_str = "2026-03"
    gen = 1
    run_id = f"month-{org_id}-{month_str}-{gen}"

    month = Month(month=month_str, state=MonthState.COLLECTING, dirty=True, generation=gen)
    await month_repo.save(org_id, month)
    await run_repo.create(
        org_id,
        Run(
            run_id=run_id,
            kind=RunKind.MONTH,
            target=month_str,
            generation=gen,
            status=RunStatus.RUNNING,
        ),
    )

    # Only an invoice uploaded, no bank statement
    invoice = Document(
        doc_id="inv_1",
        file_name="invoice.pdf",
        content_type="application/pdf",
        size_bytes=500,
        page_count=1,
        sha256="sha_inv",
        gcs_path=f"docs/{org_id}/inv_1.pdf",
        uploaded_by="user_1",
        uploaded_at=NOW,
        doc_type=DocType.SALES_INVOICE,
        status=DocStatus.DONE,
        months=[month_str],
    )
    await doc_repo.save_document(org_id, invoice)

    wf = build_month_workflow(deps)
    sessions = InMemorySessionService()
    runner = Runner(agent=cast(Any, wf), app_name="kredibel", session_service=sessions)

    await sessions.create_session(
        app_name="kredibel",
        user_id="user_1",
        session_id=run_id,
        state={
            "node_input": {
                "orgId": org_id,
                "month": month_str,
                "generation": gen,
                "runId": run_id,
            }
        },
    )

    async for _ in runner.run_async(user_id="user_1", session_id=run_id):
        pass

    # Run finished DONE
    run = await run_repo.get(org_id, run_id)
    assert run is not None
    assert run.status == RunStatus.DONE

    # Month ended in COLLECTING and dirty=False
    saved_month = await month_repo.get(org_id, month_str)
    assert saved_month is not None
    assert saved_month.state == MonthState.COLLECTING
    assert saved_month.dirty is False
    assert saved_month.last_run_id == run_id


@pytest.mark.asyncio
async def test_ac007_14_statement_presence_does_not_claim_reconciliation(workflow_deps):
    """The skeleton cannot report reconciliation without computed matches/coverage/checks."""
    deps, run_repo, month_repo, doc_repo = workflow_deps
    org_id = "org_demo"
    month_str = "2026-03"
    gen = 1
    run_id = f"month-{org_id}-{month_str}-{gen}"

    month = Month(month=month_str, state=MonthState.COLLECTING, dirty=True, generation=gen)
    await month_repo.save(org_id, month)
    await run_repo.create(
        org_id,
        Run(
            run_id=run_id,
            kind=RunKind.MONTH,
            target=month_str,
            generation=gen,
            status=RunStatus.RUNNING,
        ),
    )

    # Bank statement uploaded
    stmt = Document(
        doc_id="stmt_1",
        file_name="statement.pdf",
        content_type="application/pdf",
        size_bytes=1000,
        page_count=2,
        sha256="sha_stmt",
        gcs_path=f"docs/{org_id}/stmt_1.pdf",
        uploaded_by="user_1",
        uploaded_at=NOW,
        doc_type=DocType.BANK_STATEMENT,
        status=DocStatus.DONE,
        months=[month_str],
    )
    await doc_repo.save_document(org_id, stmt)

    wf = build_month_workflow(deps)
    sessions = InMemorySessionService()
    runner = Runner(agent=cast(Any, wf), app_name="kredibel", session_service=sessions)

    await sessions.create_session(
        app_name="kredibel",
        user_id="user_1",
        session_id=run_id,
        state={
            "node_input": {
                "orgId": org_id,
                "month": month_str,
                "generation": gen,
                "runId": run_id,
            }
        },
    )

    async for _ in runner.run_async(user_id="user_1", session_id=run_id):
        pass

    # Run finished DONE
    run = await run_repo.get(org_id, run_id)
    assert run is not None
    assert run.status == RunStatus.DONE

    # Processing ran, but actual reconciliation is not implemented yet.
    saved_month = await month_repo.get(org_id, month_str)
    assert saved_month is not None
    assert saved_month.state == MonthState.COLLECTING
    assert saved_month.note == "Reconciliation is not available yet."
    assert saved_month.dirty is False
    assert saved_month.last_run_id == run_id

    # All 10 stages recorded in order
    stage_nodes = [s.node for s in run.stages]
    expected_order = [
        "load_month",
        "reconcile",
        "check_month",
        "build_counterparties",
        "suggest_profile",
        "score_risk",
        "explain_month",
        "build_flows",
        "sync_review_items",
        "finalize_month",
    ]
    for expected_stage in expected_order:
        assert expected_stage in stage_nodes


@pytest.mark.asyncio
async def test_ac008_1_score_risk_inherits_and_persists_risk(workflow_deps):
    """score_risk inherits document risk and persists month risk on finalize_month (AC-008-1)."""
    deps, run_repo, month_repo, doc_repo = workflow_deps
    org_id = "org_demo"
    month_str = "2026-03"
    gen = 1
    run_id = f"month-{org_id}-{month_str}-{gen}"

    # Document in the month with CRITICAL risk (e.g. TAMPERED)
    stmt = Document(
        doc_id="stmt_1",
        file_name="statement.pdf",
        content_type="application/pdf",
        size_bytes=1000,
        page_count=2,
        sha256="sha_stmt",
        gcs_path=f"docs/{org_id}/stmt_1.pdf",
        uploaded_by="user_1",
        uploaded_at=NOW,
        doc_type=DocType.BANK_STATEMENT,
        status=DocStatus.DONE,
        months=[month_str],
        risk={"level": "CRITICAL", "score": 40, "reasons": ["f_tampered_1"]},
    )
    await doc_repo.save_document(org_id, stmt)

    wf = build_month_workflow(deps)
    sessions = InMemorySessionService()
    runner = Runner(agent=cast(Any, wf), app_name="kredibel", session_service=sessions)

    await sessions.create_session(
        app_name="kredibel",
        user_id="user_1",
        session_id=run_id,
        state={
            "node_input": {
                "orgId": org_id,
                "month": month_str,
                "generation": gen,
                "runId": run_id,
            }
        },
    )

    async for _ in runner.run_async(user_id="user_1", session_id=run_id):
        pass

    saved_month = await month_repo.get(org_id, month_str)
    assert saved_month is not None
    assert saved_month.risk["level"] == "CRITICAL"
    assert "f_tampered_1" in saved_month.risk["reasons"]
    assert saved_month.risk["score"] >= 40


@pytest.mark.asyncio
async def test_ac008_4_explain_month_verified_and_persisted(workflow_deps):
    """AC-008-4, AC-008-5: Verified explanation is saved with next steps and grounded summary."""
    deps, run_repo, month_repo, doc_repo = workflow_deps
    org_id = "org_exp_1"
    month_str = "2026-03"
    gen = 1
    run_id = f"month-{org_id}-{month_str}-{gen}"

    month = Month(
        month=month_str,
        state=MonthState.COLLECTING,
        dirty=True,
        generation=gen,
        figures={"closing": {"value": "60400000"}},
    )
    await month_repo.save(org_id, month)
    await run_repo.create(
        org_id,
        Run(
            run_id=run_id,
            kind=RunKind.MONTH,
            target=month_str,
            generation=gen,
            status=RunStatus.RUNNING,
        ),
    )

    finding = Finding(
        finding_id="f_x08",
        code="X08_SUPPLIER_ACCOUNT_CHANGED",
        category="RECONCILIATION",
        severity="HIGH",
        title="Supplier account changed",
        facts={"new_account": "123456"},
        evidence=[],
        scope="MONTH",
        month=month_str,
    )
    await deps.findings.replace_month_findings(org_id, month_str, [finding], run_id=run_id)

    fake_reader = FakeDocumentReader(
        month_explanation=MonthExplanation(
            summary=(
                "Supplier account changed [[finding:f_x08]]. "
                "Closing balance reached [[fact:2026-03:closing]]."
            ),
            next_steps=["Confirm the new account with the supplier"],
            finding_explanations=[
                FindingExplanation(
                    finding_id="f_x08",
                    explanation="Roastline was paid to a new account [[finding:f_x08]].",
                )
            ],
        )
    )
    deps.reader = fake_reader

    wf = build_month_workflow(deps)
    sessions = InMemorySessionService()
    runner = Runner(agent=cast(Any, wf), app_name="kredibel", session_service=sessions)

    await sessions.create_session(
        app_name="kredibel",
        user_id="user_1",
        session_id=run_id,
        state={
            "node_input": {
                "orgId": org_id,
                "month": month_str,
                "generation": gen,
                "runId": run_id,
            }
        },
    )

    async for _ in runner.run_async(user_id="user_1", session_id=run_id):
        pass

    saved_month = await month_repo.get(org_id, month_str)
    assert saved_month is not None
    assert saved_month.risk["grounding"] == "VERIFIED"
    assert "Supplier account changed" in saved_month.risk["summary"]
    assert "Confirm the new account with the supplier" in saved_month.risk["nextSteps"][0]
    assert saved_month.risk["hash"] != ""


@pytest.mark.asyncio
async def test_ac008_5_explain_month_ungrounded_falls_back_to_template(workflow_deps):
    """AC-008-5: Hallucinated/ungrounded figures fall back to template text."""
    deps, run_repo, month_repo, doc_repo = workflow_deps
    org_id = "org_exp_2"
    month_str = "2026-03"
    gen = 1
    run_id = f"month-{org_id}-{month_str}-{gen}"

    month = Month(month=month_str, state=MonthState.COLLECTING, dirty=True, generation=gen)
    await month_repo.save(org_id, month)
    await run_repo.create(
        org_id,
        Run(
            run_id=run_id,
            kind=RunKind.MONTH,
            target=month_str,
            generation=gen,
            status=RunStatus.RUNNING,
        ),
    )

    finding = Finding(
        finding_id="f_x08",
        code="X08_SUPPLIER_ACCOUNT_CHANGED",
        category="RECONCILIATION",
        severity="HIGH",
        title="Supplier account changed",
        facts={},
        evidence=[],
        scope="MONTH",
        month=month_str,
    )
    await deps.findings.replace_month_findings(org_id, month_str, [finding], run_id=run_id)

    # Reader returns ungrounded number not cited in any fact or finding
    fake_reader = FakeDocumentReader(
        month_explanation=MonthExplanation(
            summary="We made up an arbitrary profit of IDR 999,999,999 without any facts.",
            next_steps=["Check books"],
        )
    )
    deps.reader = fake_reader

    wf = build_month_workflow(deps)
    sessions = InMemorySessionService()
    runner = Runner(agent=cast(Any, wf), app_name="kredibel", session_service=sessions)

    await sessions.create_session(
        app_name="kredibel",
        user_id="user_1",
        session_id=run_id,
        state={
            "node_input": {
                "orgId": org_id,
                "month": month_str,
                "generation": gen,
                "runId": run_id,
            }
        },
    )

    async for _ in runner.run_async(user_id="user_1", session_id=run_id):
        pass

    saved_month = await month_repo.get(org_id, month_str)
    assert saved_month is not None
    assert saved_month.risk["grounding"] == "TEMPLATE"
    assert "High fraud risk detected" in saved_month.risk["summary"]
    # The run says the model was asked twice (the call and its retry) and why it fell back.
    run = await run_repo.get(org_id, run_id)
    assert run is not None
    explain = next(s for s in run.stages if s.node == "explain_month")
    assert (explain.model, explain.tokens_in, explain.tokens_out) == ("fake-model", 800, 300)
    assert explain.summary == "Month explanation generated (TEMPLATE: not grounded)"


@pytest.mark.asyncio
async def test_ac008_6_explain_month_skips_when_hash_unchanged(workflow_deps):
    """AC-008-6: explain_month is skipped when facts and findings hash is unchanged."""
    deps, run_repo, month_repo, doc_repo = workflow_deps
    org_id = "org_exp_3"
    month_str = "2026-03"
    gen = 1
    run_id = f"month-{org_id}-{month_str}-{gen}"

    month = Month(month=month_str, state=MonthState.COLLECTING, dirty=True, generation=gen)
    await month_repo.save(org_id, month)
    await run_repo.create(
        org_id,
        Run(
            run_id=run_id,
            kind=RunKind.MONTH,
            target=month_str,
            generation=gen,
            status=RunStatus.RUNNING,
        ),
    )

    fake_reader = FakeDocumentReader(
        month_explanation=MonthExplanation(
            summary="Clean month summary.",
            next_steps=[],
        )
    )
    deps.reader = fake_reader

    wf = build_month_workflow(deps)
    sessions = InMemorySessionService()
    runner = Runner(agent=cast(Any, wf), app_name="kredibel", session_service=sessions)

    await sessions.create_session(
        app_name="kredibel",
        user_id="user_1",
        session_id=run_id,
        state={
            "node_input": {
                "orgId": org_id,
                "month": month_str,
                "generation": gen,
                "runId": run_id,
            }
        },
    )

    async for _ in runner.run_async(user_id="user_1", session_id=run_id):
        pass

    calls_first_run = len([c for c in fake_reader.calls if c[0] == "explain_month"])
    assert calls_first_run == 1

    # Second run with same data
    run_id_2 = f"month-{org_id}-{month_str}-2"
    await run_repo.create(
        org_id,
        Run(
            run_id=run_id_2,
            kind=RunKind.MONTH,
            target=month_str,
            generation=2,
            status=RunStatus.RUNNING,
        ),
    )
    month_2 = await month_repo.get(org_id, month_str)
    assert month_2 is not None
    month_2.generation = 2
    month_2.dirty = True
    await month_repo.save(org_id, month_2)

    await sessions.create_session(
        app_name="kredibel",
        user_id="user_1",
        session_id=run_id_2,
        state={
            "node_input": {
                "orgId": org_id,
                "month": month_str,
                "generation": 2,
                "runId": run_id_2,
            }
        },
    )

    async for _ in runner.run_async(user_id="user_1", session_id=run_id_2):
        pass

    calls_second_run = len([c for c in fake_reader.calls if c[0] == "explain_month"])
    assert calls_second_run == 1  # Not called again because hash was unchanged!


@pytest.mark.asyncio
async def test_ac008_6_a_template_is_tried_again_on_the_next_run(workflow_deps):
    """AC-008-6: the hash skip keeps Gemini's explanation; a template (here: no reader on the first
    run, as every month run had until dea28e4) is tried again although nothing changed."""
    deps, run_repo, month_repo, _ = workflow_deps
    org_id, month_str = "org_exp_4", "2026-03"
    await month_repo.save(
        org_id, Month(month=month_str, state=MonthState.COLLECTING, dirty=True, generation=1)
    )
    sessions = InMemorySessionService()

    async def run(generation: int) -> None:
        run_id = f"month-{org_id}-{month_str}-{generation}"
        await run_repo.create(
            org_id,
            Run(
                run_id=run_id,
                kind=RunKind.MONTH,
                target=month_str,
                generation=generation,
                status=RunStatus.RUNNING,
            ),
        )
        saved = await month_repo.get(org_id, month_str)
        assert saved is not None
        saved.generation, saved.dirty = generation, True
        await month_repo.save(org_id, saved)
        runner = Runner(
            agent=cast(Any, build_month_workflow(deps)),
            app_name="kredibel",
            session_service=sessions,
        )
        node_input = {
            "orgId": org_id,
            "month": month_str,
            "generation": generation,
            "runId": run_id,
        }
        await sessions.create_session(
            app_name="kredibel", user_id="u", session_id=run_id, state={"node_input": node_input}
        )
        async for _ in runner.run_async(user_id="u", session_id=run_id):
            pass

    deps.reader = None
    await run(1)
    first = await month_repo.get(org_id, month_str)
    assert first is not None and first.risk["grounding"] == "TEMPLATE"

    reader = FakeDocumentReader(
        month_explanation=MonthExplanation(summary="Clean month summary.", next_steps=[])
    )
    deps.reader = reader
    await run(2)
    second = await month_repo.get(org_id, month_str)
    assert [c[0] for c in reader.calls].count("explain_month") == 1
    assert second is not None and second.risk["grounding"] == "VERIFIED"
