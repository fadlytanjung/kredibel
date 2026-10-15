"""One run is one trace (AC-004-12, docs/17 §2, docs/23): a `workflow:` root span, every node span
inside it, the trace ID stored on the run, and ADK sessions keyed by `{orgId}:system`."""

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.agents.deps import PipelineDeps
from app.agents.runtime import adk_user_id, run_workflow
from app.agents.workflows.month_workflow import build_month_workflow
from app.core.settings import Settings
from app.domain.models.month import Month, MonthState
from app.domain.models.run import Run, RunKind
from tests.fakes.document_repository import FakeDocumentRepository
from tests.fakes.month_repository import FakeMonthRepository
from tests.fakes.run_repository import FakeRunRepository

_EXPORTER = InMemorySpanExporter()


def _trace_id(span: ReadableSpan) -> int:
    context = span.get_span_context()
    assert context is not None
    return context.trace_id


@pytest.fixture(scope="module", autouse=True)
def _sdk_tracer():
    # The global provider can be set once per process; reuse it when another test already did.
    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
    provider.add_span_processor(SimpleSpanProcessor(_EXPORTER))


async def test_ac004_12_a_month_run_is_one_trace_recorded_on_the_run():
    _EXPORTER.clear()
    runs = FakeRunRepository()
    await runs.create("org_t", Run(run_id="run_t", kind=RunKind.MONTH, target="2026-03"))
    months = FakeMonthRepository()
    months.months[("org_t", "2026-03")] = Month(
        month="2026-03", generation=1, state=MonthState.COLLECTING
    )
    deps = PipelineDeps(
        settings=Settings(),
        run_repo=runs,
        doc_repo=FakeDocumentRepository(),
        month_repo=months,
    )

    await run_workflow(
        build_month_workflow(deps),
        org_id="org_t",
        run_id="run_t",
        node_input={"orgId": "org_t", "month": "2026-03", "generation": 1, "runId": "run_t"},
        run_repo=runs,
        settings=deps.settings,
    )

    spans = _EXPORTER.get_finished_spans()
    [root] = [s for s in spans if s.name == "workflow:month_workflow"]
    assert root.attributes is not None
    assert root.attributes["runId"] == "run_t"
    assert root.attributes["orgId"] == "org_t"
    # Langfuse groups a month's runs by session, workspaces by user (ADR-026).
    assert root.attributes["langfuse.trace.name"] == "month_workflow"
    # Identifiers in, outcome out; no document content (ADR-026).
    assert root.attributes["langfuse.observation.input"] == (
        '{"generation": "1", "month": "2026-03", "runId": "run_t", "workflow": "month_workflow"}'
    )
    assert root.attributes["langfuse.observation.output"] == '{"outcome": "done"}'
    assert root.attributes["langfuse.session.id"] == "month:2026-03"
    assert root.attributes["langfuse.user.id"] == "org_t"
    assert root.attributes["langfuse.trace.tags"] == ("month_workflow",)
    node_spans = [s for s in spans if s.name.startswith("node:")]
    assert node_spans, "node spans were not recorded"
    assert {_trace_id(s) for s in node_spans} == {_trace_id(root)}

    run = await runs.get("org_t", "run_t")
    assert run is not None
    assert run.trace_id == format(_trace_id(root), "032x")


def test_adr017_adk_user_ids_start_with_the_workspace():
    assert adk_user_id("org_t") == "org_t:system"


async def test_ac004_12_the_adk_session_is_the_run():
    """ADK names the session in its spans (gen_ai.conversation.id); it is our run ID."""
    _EXPORTER.clear()
    runs = FakeRunRepository()
    await runs.create("org_t", Run(run_id="run_u", kind=RunKind.MONTH, target="2026-03"))
    months = FakeMonthRepository()
    months.months[("org_t", "2026-03")] = Month(
        month="2026-03", generation=1, state=MonthState.COLLECTING
    )
    deps = PipelineDeps(
        settings=Settings(), run_repo=runs, doc_repo=FakeDocumentRepository(), month_repo=months
    )

    await run_workflow(
        build_month_workflow(deps),
        org_id="org_t",
        run_id="run_u",
        node_input={"orgId": "org_t", "month": "2026-03", "generation": 1, "runId": "run_u"},
        run_repo=runs,
        settings=deps.settings,
    )

    [workflow_span] = [
        s for s in _EXPORTER.get_finished_spans() if s.name == "invoke_workflow month_workflow"
    ]
    assert workflow_span.attributes is not None
    assert workflow_span.attributes["gen_ai.conversation.id"] == "run_u"


async def test_ac004_12_a_run_started_inside_another_run_is_its_own_trace():
    """The inline queue runs a month task inside the document run that queued it; on Cloud Run it
    is its own request. Either way the month run is its own trace, linked to the run that caused
    it (Langfuse and Cloud Trace list one run per trace)."""
    _EXPORTER.clear()
    runs = FakeRunRepository()
    await runs.create("org_t", Run(run_id="run_m", kind=RunKind.MONTH, target="2026-03"))
    months = FakeMonthRepository()
    months.months[("org_t", "2026-03")] = Month(
        month="2026-03", generation=1, state=MonthState.COLLECTING
    )
    deps = PipelineDeps(
        settings=Settings(), run_repo=runs, doc_repo=FakeDocumentRepository(), month_repo=months
    )
    tracer = trace.get_tracer("test")
    with tracer.start_as_current_span("workflow:document_workflow") as outer:
        await run_workflow(
            build_month_workflow(deps),
            org_id="org_t",
            run_id="run_m",
            node_input={"orgId": "org_t", "month": "2026-03", "generation": 1, "runId": "run_m"},
            run_repo=runs,
            settings=deps.settings,
        )
    [month_root] = [
        s for s in _EXPORTER.get_finished_spans() if s.name == "workflow:month_workflow"
    ]
    assert _trace_id(month_root) != outer.get_span_context().trace_id
    assert month_root.parent is None
    assert [link.context.span_id for link in month_root.links] == [outer.get_span_context().span_id]
