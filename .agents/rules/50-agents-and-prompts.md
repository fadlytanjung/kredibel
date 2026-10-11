---
trigger: glob
globs: backend/app/agents/**
description: Rules for ADK workflow nodes, LLM agents and prompt files.
---

# Agents, nodes and prompts

- Nodes are created by factories (`def x(deps) -> node`) that close over injected adapters; no globals.
- Every node: reports progress (`ProgressReporter`), checks its idempotency key before working, writes
  its results with deterministic IDs, and returns a **small** summary (IDs, counts, verdicts). Large
  data stays in Firestore/GCS, never in workflow state.
- Node names and order must match `docs/06-agent-design.md` §2–§4 and `domain/models/run.py`.
- `month_workflow` writes only in `finalize_month` after the generation check; never write month
  results from another node.
- Prompts live in `agents/prompts/<id>.md` with front matter `id`, `version`, `model_env`,
  `output_schema`. Bump `version` on any prompt change and re-record affected scenario recordings.
- Prompts that see document content include the untrusted-content framing and pass the document as a
  separate content part.
- Page-reading prompts ask for values **as printed** (strings) from **one page image**; normalization
  happens in `domain/normalize.py`, verification in `domain/verify.py`.
- LLM prose (explanations, assistant answers) is written in English with `[[…]]` citation markers;
  prompts say so explicitly. The grounding guard runs on every one.
- Temperature 0 for classification, reading, ledger mapping, categorization and visual examination;
  ≤ 0.2 for prose.
- The ledger mapper sees the header and value shapes only, never descriptions, names or amounts.
- The assistant's tools are read-only, return values with fact IDs, and read `org_id`/`uid` from
  session state set by the server; retrieved chunks are framed as untrusted text.
- When the ADK API differs from the docs, follow the installed version, then update
  `docs/06-agent-design.md` in the same commit.
- Every classification, page type and category a node decides is written as a label with its
  confidence, model, prompt version, `runId`, `traceId` and `spanId` (`services/label_writer.py`); a
  node never changes a label a person confirmed or corrected (ADR-016).
- Verified examples in a prompt come only from the same workspace, sit inside the untrusted-data
  framing, and are at most `learning.v1.yaml` `examples.perCall`.
- Content capture follows `AI_CONTENT_CAPTURE` (ADR-017): never set `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS`
  or plugin content options by hand; debug a node with `make dev-agents`.
