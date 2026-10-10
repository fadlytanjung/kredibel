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
- Node names and order must match the stage list in `docs/06-agent-design.md` §3 and
  `domain/models/run.py`.
- Prompts live in `agents/prompts/<id>.md` with front matter `id`, `version`, `model_env`,
  `output_schema`. Bump `version` on any prompt change and re-record affected scenario recordings.
- Prompts that see document content include the untrusted-content framing and pass the document as a
  separate content part.
- Page-reading prompts ask for values **as printed** (strings) from **one page image**; normalization
  happens in `domain/normalize.py`, verification in `domain/verify.py`.
- LLM prose (memo, explanations) is written in English; prompts say so explicitly.
- Temperature 0 for classification, extraction, categorization and visual examination; ≤ 0.2 for
  prose.
- The assistant's tools are read-only and read `org_id`/`case_id` from session state set by the server.
- When the ADK API differs from the docs, follow the installed version, then update
  `docs/06-agent-design.md` in the same commit.
