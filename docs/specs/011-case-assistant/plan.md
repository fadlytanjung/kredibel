# Plan 011 — Case Assistant

| File | Content |
|---|---|
| `agents/tools/case_tools.py` | the 7 read-only tools of docs/06 §9; each reads `tool_context.state["org_id"]`/`["case_id"]`; returns small JSON with IDs |
| `agents/prompts/case_assistant.md` | role, scope, citation format, refusal rules, untrusted-data note (tool results may contain document text) |
| `agents/assistant.py` | `Agent(name="case_assistant", model=MODEL_FAST, tools=[…])`; `Runner` with `VertexAiSessionService` (`AGENT_SESSIONS_RESOURCE`) or `InMemorySessionService` locally |
| `services/assistant_service.py` | get/create session `(uid, caseId)` with server-set state; run; extract reply + markers; store display copies in `assistantMessages` |
| `api/assistant.py` | `GET`/`POST …/assistant/messages` |
| `backend/scripts/create_sessions_resource.py` | creates the Agent Runtime resource used only for Sessions; prints `AGENT_SESSIONS_RESOURCE` |
| `widgets/AssistantDrawer/`, `features/ask-assistant/` | drawer, suggested questions, citation chips |
| `backend/evals/assistant/*.evalset.json` | ADK eval cases |

Constitution check: P4 ✔ (read-only, server-scoped) · P3 ✔ (citations) · P7 ✔ (ADK, Agent Platform Sessions)
