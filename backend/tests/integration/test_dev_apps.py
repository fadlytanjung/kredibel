"""Every agent and workflow can be opened and run in the ADK dev UI (`make dev-agents`, T017-01).

The test loads each dev app the way `adk web` does and sends it a chat message, so an app that
cannot be imported or a node that cannot take the dev UI's input fails here, not in front of a
developer.
"""

import json
from pathlib import Path
from typing import Any, cast

import pytest
from google.adk.cli.utils.agent_loader import AgentLoader
from google.adk.runners import InMemoryRunner
from google.genai import types

DEV_APPS = Path(__file__).resolve().parents[2] / "app" / "agents" / "dev_apps"
APPS = sorted(p.name for p in DEV_APPS.iterdir() if (p / "agent.py").is_file())

RUN_INPUT = {
    "document_workflow": {"orgId": "org_dev", "docId": "doc_sample_1", "runId": "run_dev"},
    "month_workflow": {"orgId": "org_dev", "month": "2026-03", "generation": 1, "runId": "run_dev"},
}


def test_t017_01_there_is_a_dev_app_for_each_workflow():
    assert {"document_workflow", "month_workflow"} <= set(APPS)


async def _run(app: str, message: str, state: dict | None = None) -> list:
    agent = AgentLoader(str(DEV_APPS)).load_agent(app)
    # A Workflow is an ADK node rather than a BaseAgent; Runner accepts both at run time.
    runner = InMemoryRunner(agent=cast(Any, agent), app_name=app)
    session = await runner.session_service.create_session(app_name=app, user_id="dev", state=state)
    content = types.Content(role="user", parts=[types.Part(text=message)])
    return [
        e async for e in runner.run_async(user_id="dev", session_id=session.id, new_message=content)
    ]


@pytest.mark.parametrize("app", APPS)
async def test_t017_01_a_dev_app_runs_from_a_json_message(app):
    events = await _run(app, json.dumps(RUN_INPUT[app]))

    nodes = [e.node_info.path.rsplit("/", 1)[-1] for e in events if getattr(e, "node_info", None)]
    assert nodes, f"{app} produced no node events"


@pytest.mark.parametrize("app", APPS)
async def test_t017_01_a_dev_app_runs_from_session_state_with_any_message(app):
    events = await _run(app, "run", state={"node_input": RUN_INPUT[app]})

    assert any(getattr(e, "node_info", None) for e in events)
