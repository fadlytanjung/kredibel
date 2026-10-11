---
name: adk-workflow-node
description: Adds or replaces a node in Kredibel's ADK document_workflow or month_workflow (function node or LLM agent node) with the project's factory, idempotency, stage recording and testing conventions. Use when implementing workflow stages such as reading, checks, duplicates, reconciliation, risk scoring, explanations or money flows.
---

# Add or replace a workflow node

## 1. Contract first

Find the node in `docs/06-agent-design.md` §4: kind (function/LLM), what it writes, idempotency key,
priority. If it is new, add a row there first, add it to the workflow shape in §2 or §3, and add its
stage name to `domain/models/run.py`.

## 2. Logic in the domain

Put any computation in `backend/app/domain/…` as pure functions with unit tests. The node only
orchestrates: load → call domain or gateway → persist → return a small summary.

## 3. Factory

```python
# backend/app/agents/nodes/month_nodes.py
def build_flows(deps: PipelineDeps):
    @node(name="build_flows")
    async def _node(ctx: Context, node_input: dict) -> dict:
        org_id, month = node_input["orgId"], node_input["month"]
        lines = await deps.repo.list_bank_lines(org_id, month, include_held=False)  # data from Firestore
        accounts = await deps.repo.list_bank_accounts(org_id)
        flow = money_flow.build(lines, accounts, options=deps.policy.money_flow)    # pure domain
        return {**node_input, "flows": flow.summary()}                              # small summary
    return stage(deps, "build_flows", _node)        # records the stage, binds logs, opens a span
```

Month nodes never write month results directly: `finalize_month` writes everything after the
generation check (docs/06 §3). Document nodes write their records with deterministic IDs.
Adjust the decorator import and signature to the installed ADK version (docs/06 §2.2).

## 4. LLM nodes

- Prompt file `agents/prompts/<id>.md` with front matter (`id`, `version`, `model_env`,
  `output_schema`); untrusted-content framing if it sees document content; the ledger mapper sees
  shapes only.
- Output schema in `agents/llm/schemas.py`.
- Multimodal calls: `deps.gemini.generate_structured(...)` (gateway handles retries, schema retry,
  quarantine guard, labels, usage). Text steps: ADK `Agent(..., output_schema=...)` via `ctx.run_node`.
- Prose (explanations) goes through the grounding guard with a template fallback.
- Record outputs for scenarios (`make record`) and add eval cases.

## 5. Idempotency and order independence

Check the node's idempotency key before working; use deterministic IDs; upsert. Re-running the node
for the same inputs must produce identical stored results, whatever order the documents arrived in.

## 6. Tests

- Unit tests for the domain functions (property tests where order or arithmetic matters).
- Node test with fakes (`tests/fakes/`) asserting writes, the stage record and the returned summary.
- Scenario test updated if the node changes expected outcomes (compare to `truth.json`).
