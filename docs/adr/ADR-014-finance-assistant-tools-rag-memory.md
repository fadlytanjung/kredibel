# ADR-014 — Finance Assistant: tools first, Firestore retrieval, Memory Bank for preferences

**Status:** Accepted for P1 · **Date:** 2026-10-10 · **Related:** [ADR-002](ADR-002-cloud-run-not-agent-runtime.md),
[ADR-003](ADR-003-firestore-system-of-record.md), [ADR-015](ADR-015-scope-finance-workspace-not-loan-review.md)

## Context

Users want to ask about their books in plain language: "How much did we pay Green Valley Farms in
March?", "Why is April high risk?", "Which invoices are still unpaid?". The answers live in three
different places:

1. **Computed facts**: month figures, matches, findings, review items, the money flow. These are
   exact and already in Firestore.
2. **Document text**: what an invoice or statement actually says (terms, descriptions, notes).
3. **Kredibel's own knowledge**: what a check means, how the risk level is set, how to fix a
   review item.

On top of that, the assistant should remember a user's **preferences** across conversations ("show
amounts in thousands", "our fiscal year starts in April", "the ACB ••5577 account is for
payroll").

Google Cloud offers several ways to do each part. We need the one that is accurate, cheap at hackathon
scale, and does not add a second system of record.

## Decision

1. **Tools first, retrieval second.** Numbers come only from read-only tools that query Firestore
   (`get_period_summary`, `get_money_flow`, `search_bank_lines`, `list_findings`,
   `list_review_items`, `explain_figure`, …). Retrieval is used for words, never for figures.
   The model never computes totals from retrieved text.
2. **Retrieval uses Firestore vector search** on `orgs/{orgId}/retrievalChunks` (one chunk per page
   or ledger block, `embedding_v1` 768 dimensions, cosine, `gemini-embedding-001`). A second,
   global collection `knowledgeChunks` holds the policy files, the check catalog and help pages. The
   same database, rules, backups and migrations apply (ADR-003, ADR-013). Chunks are written by the
   `document_workflow` after reading, and their text is framed as **untrusted** in the prompt.
3. **Conversation state uses Agent Platform Sessions** (`VertexAiSessionService`) and **long-term
   memory uses Memory Bank** (`VertexAiMemoryBankService` + `PreloadMemoryTool`). Both are created
   once by a bootstrap script **without deploying any agent code**: a Memory Bank
   (`client.memory_banks.create()`) and a Sessions container (an Agent Runtime instance with no
   agent); their IDs are configuration (`MEMORY_BANK_ID`, `AGENT_SESSIONS_ID`; one ID for both if
   spike S5 shows one instance serves both). The agent itself keeps running inside `kredibel-web` on
   Cloud Run (ADR-002 stands). New events are sent to Memory Bank incrementally
   (`add_events_to_memory` from an `after_agent_callback`); generation runs in the background.
4. **Memory scope = workspace + user.** The Memory Bank `user_id` is `"{orgId}:{uid}"`, so memories
   never cross workspaces or users. Memory generation uses a **custom topic list** limited to
   preferences: display preferences, fiscal calendar, account nicknames, counterparties the user
   says are related or trusted. Financial figures, findings and document content are never stored as
   memories; they are always re-read from Firestore.
5. **Grounding guard on every answer** (the same guard as the month explanation, [`06`](../06-agent-design.md) §5.1):
   every number in the answer must match a value returned by a tool in that turn, and every cited
   fact, document or finding ID must exist. On failure the answer is replaced by the tool results
   rendered as a table with a short "I could not phrase this safely" note.
6. **Charts in answers** are structured parts, not images: `get_money_flow` and
   `get_period_summary` return data the UI renders with the same Sankey and bar components as the
   dashboard.
7. **Limits:** `assistantQuestionsPerDay` from the plan, a per-turn cap of 6 tool calls, and the
   shared monthly AI spend limit.

## Consequences

- Accurate numbers: the assistant cannot invent a figure that the books do not contain, and it
  shows the same values as the dashboard.
- One database: retrieval, data and access rules stay in Firestore; deleting a document deletes its
  chunks (a domain event, [`09`](../09-data-model.md) §8).
- Memory Bank and Sessions add managed dependencies that do no serving of our code. Sessions and
  memories are deleted when the workspace is deleted (purge by `user_id` prefix).
- Firestore vector search uses flat (exact) indexes. That is fine for thousands of chunks per
  workspace; beyond that we revisit (see alternatives).
- Answers are evaluated with DeepEval using a Gemini judge on Agent Platform
  ([`15`](../15-testing-and-evaluation.md) §5.1): faithfulness, answer relevancy, contextual recall and
  tool correctness.

## Alternatives considered

| Option | Why not (for now) |
|---|---|
| Agent Platform RAG Engine with RagManagedDb | Managed and good, but RagManagedDb runs on Spanner (the Basic tier is 100 processing units), a fixed monthly cost far above our usage; can be switched in behind `search_documents` later |
| Vector Search 2.0 / a dedicated index | Needs an always-on endpoint; over-built for thousands of chunks |
| Answer from retrieval alone (classic RAG over everything) | Figures would come from text, not from the reconciled data; totals would be wrong or stale |
| Our own memory collection in Firestore | Possible, but Memory Bank already extracts, merges and expires memories; re-building that is not our product |
| Deploy the assistant to Agent Runtime | Two serving platforms for one prototype; auth and rate limits already live in `kredibel-web` |
| No memory | Acceptable fallback: the assistant still works with sessions only (`ASSISTANT_MEMORY=off`) |

## Verify on day 0

- Memory Bank and Sessions availability in the chosen region (a multi-regional Memory Bank such as
  `us` can serve a regional runtime), custom memory topics and time to live, and current pricing
  (third-party sources quote a per-GiB-month storage price and per-vCPU-hour processing with a small
  free tier; the official pricing page wins).
- Firestore vector search limits (dimension 768 supported, `find_nearest` with a pre-filter on
  `source` and `month`).
