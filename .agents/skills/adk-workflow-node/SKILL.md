---
name: adk-workflow-node
description: Adds or replaces a node in Kredibel's ADK case_pipeline workflow (function node or LLM agent node) with the project's factory, idempotency, progress and testing conventions. Use when implementing pipeline stages such as extraction, checks, categorization, scoring or memo drafting.
---

# Add or replace a workflow node

## 1. Contract first

Find the node in `docs/06-agent-design.md` §3: kind (function/LLM), reads, writes, idempotency key,
timeout. If it is new, add a row there first, and add its stage name to `domain/models/run.py` in
pipeline order.

## 2. Logic in the domain

Put any computation in `backend/app/domain/…` as pure functions with unit tests. The node only
orchestrates: load → call domain/gateway → persist → report.

## 3. Factory

```python
# backend/app/agents/nodes/case_nodes.py
def compute_cashflow_metrics(deps: PipelineDeps):
    @node(name="compute_cashflow_metrics")
    async def _node(ctx: Context, node_input: dict) -> dict:
        run_id, case_ref = node_input["runId"], node_input["case"]
        await deps.progress.stage_started(case_ref, run_id, "compute_cashflow_metrics")
        txs = await deps.repo.list_transactions(case_ref)            # large data from Firestore
        result = metrics.compute(txs, deps.policy.scorecard, case_ref.request)   # pure domain
        await deps.repo.put_analysis(case_ref, run_id, monthly=result.monthly, facts=result.facts)
        await deps.progress.stage_finished(case_ref, run_id, "compute_cashflow_metrics")
        return {**node_input, "factsCount": len(result.facts)}       # small summary only
    return _node
```

(Adjust decorator import/signature to the installed ADK version; see docs/06 §2.3.)

## 4. LLM nodes

- Prompt file `agents/prompts/<id>.md` with front matter (`id`, `version`, `model_env`,
  `output_schema`); untrusted-content framing if it sees document content.
- Output schema in `agents/llm/schemas.py`.
- Multimodal calls: `deps.gemini.generate_structured(...)` (gateway handles retries, schema retry,
  quarantine guard, labels, usage). Text reasoning: ADK `Agent(..., output_schema=...)` run via
  `ctx.run_node`.
- Record outputs for scenarios (`make record`) and add eval cases.

## 5. Idempotency

Check the node's idempotency key before working; use deterministic IDs; upsert. Re-running the node
for the same run must produce identical stored results.

## 6. Tests

- Unit tests for the domain functions.
- Node test with fakes (`tests/fakes/`) asserting writes, progress calls and the returned summary.
- Scenario test updated if the node changes expected outcomes (compare to `truth.json`).
