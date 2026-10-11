"""Unit tests for stages.py node execution wrapper (T004-05, AC-004-1, AC-004-12)."""

from datetime import UTC, datetime
from typing import Any, cast

import pytest
from google.adk import Context, Runner, Workflow
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import node
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from app.agents.deps import PipelineDeps
from app.agents.stages import stage
from app.core.settings import Settings
from app.domain.models.run import Run, RunKind, RunStatus, StageStatus
from tests.fakes.clock import FixedClock
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.month_repository import FakeMonthRepository
from tests.fakes.run_repository import FakeRunRepository

NOW = datetime(2026, 3, 15, 10, 0, tzinfo=UTC)

# Configure OpenTelemetry TracerProvider once for tests
trace.set_tracer_provider(TracerProvider())


@pytest.fixture
def test_deps():
    settings = Settings()
    run_repo = FakeRunRepository()
    clock = FixedClock(NOW)
    deps = PipelineDeps(
        settings=settings,
        run_repo=run_repo,
        doc_repo=FakeDocumentRepository(),
        month_repo=FakeMonthRepository(),
        clock=clock,
    )
    return deps, run_repo


@pytest.mark.asyncio
async def test_stage_success_appends_stage_record(test_deps):
    """Successful node execution records RunStage with status DONE, summary, and span id."""
    deps, run_repo = test_deps
    run = Run(run_id="run_1", kind=RunKind.DOCUMENT, target="doc_1", status=RunStatus.RUNNING)
    await run_repo.create("org_1", run)

    @stage(deps, "sample_node")
    async def sample_node(ctx: Context, node_input: dict) -> dict:
        return {
            **node_input,
            "status": "PROCESSED",
            "summary": "Sample step completed",
            "model": "gemini-3.8-flash",
            "tokens_in": 100,
            "tokens_out": 50,
        }

    input_data = {"orgId": "org_1", "runId": "run_1", "docId": "doc_1"}
    res = await sample_node(None, input_data)

    assert res["status"] == "PROCESSED"
    assert res["summary"] == "Sample step completed"

    fetched = await run_repo.get("org_1", "run_1")
    assert fetched is not None
    assert len(fetched.stages) == 1
    s = fetched.stages[0]
    assert s.node == "sample_node"
    assert s.status == StageStatus.DONE
    assert s.summary == "Sample step completed"
    assert s.model == "gemini-3.8-flash"
    assert s.tokens_in == 100
    assert s.tokens_out == 50
    assert s.started_at == NOW
    assert s.ended_at == NOW
    assert s.trace_span_id is not None


@pytest.mark.asyncio
async def test_stage_failure_records_failed_stage_and_reraises(test_deps):
    """Failing node records RunStage with status FAILED and re-raises the exception."""
    deps, run_repo = test_deps
    run = Run(run_id="run_2", kind=RunKind.DOCUMENT, target="doc_2", status=RunStatus.RUNNING)
    await run_repo.create("org_1", run)

    @stage(deps, "failing_node")
    async def failing_node(ctx: Context, node_input: dict) -> dict:
        raise ValueError("Corrupt PDF file header")

    input_data = {"orgId": "org_1", "runId": "run_2", "docId": "doc_2"}
    with pytest.raises(ValueError, match="Corrupt PDF file header"):
        await failing_node(None, input_data)

    fetched = await run_repo.get("org_1", "run_2")
    assert fetched is not None
    assert len(fetched.stages) == 1
    s = fetched.stages[0]
    assert s.node == "failing_node"
    assert s.status == StageStatus.FAILED
    assert "Corrupt PDF file header" in (s.summary or "")


@pytest.mark.asyncio
async def test_stage_inside_adk_workflow_execution(test_deps):
    """Wrapped node runs seamlessly inside an ADK Workflow driven by Runner."""
    deps, run_repo = test_deps
    run = Run(run_id="run_3", kind=RunKind.DOCUMENT, target="doc_3", status=RunStatus.RUNNING)
    await run_repo.create("org_1", run)

    child_node = stage(
        deps,
        "adk_child",
        lambda ctx, inp: {**inp, "count": inp.get("count", 0) + 1, "summary": "child done"},
    )

    @node(name="adk_parent", rerun_on_resume=True)
    async def adk_parent(ctx: Context, data: dict | None = None) -> dict:
        return await ctx.run_node(child_node, {"orgId": "org_1", "runId": "run_3", "count": 10})


    wf = Workflow(name="test_wf", edges=[("START", adk_parent)])
    sessions = InMemorySessionService()
    runner = Runner(agent=cast(Any, wf), app_name="kredibel", session_service=sessions)


    await sessions.create_session(app_name="kredibel", user_id="u1", session_id="s1")
    async for _ in runner.run_async(user_id="u1", session_id="s1"):
        pass

    fetched = await run_repo.get("org_1", "run_3")
    assert fetched is not None
    assert len(fetched.stages) == 1
    assert fetched.stages[0].node == "adk_child"
    assert fetched.stages[0].status == StageStatus.DONE
    assert fetched.stages[0].summary == "child done"
