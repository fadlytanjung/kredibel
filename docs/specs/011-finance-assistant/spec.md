# Spec 011 — Finance Assistant

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P1 (starts only when P0 is green, constitution P9) |
| **Owner role** | A: Agents (+ C for the chat screen) |
| **Depends on** | 007, 008, 010 |
| **Requirements** | FR-070, P1-01, NFR-10 |
| **Design** | [ADR-014](../../adr/ADR-014-finance-assistant-tools-rag-memory.md); [`docs/06`](../../06-agent-design.md) §10; [`docs/15`](../../15-testing-and-evaluation.md) §5.1–§5.2 |

## Summary

A chat that answers questions about the workspace's books — "How much did we pay Green Valley Farms
in March?", "Why is March critical?", "Which invoices are unpaid?" — with numbers from **read-only
tools**, words from **retrieval** over document text and Kredibel's help, charts as structured parts,
and **memory** of the user's preferences through Agent Platform Sessions and Memory Bank. Every number
is checked by the grounding guard; quality is measured with DeepEval.

## User stories

### US-011-1: Ask about my books

- **AC-011-1** `POST /api/assistant/threads/{id}/messages` runs `finance_assistant` (ADK `Agent`,
  `MODEL_FAST`) with the tools of [`docs/06`](../../06-agent-design.md) §10; `orgId` and `uid` come
  from server-set session state; at most 6 tool calls per turn; `assistantQuestionsPerDay` enforced.
- **AC-011-2** Figures come only from tools; every value a tool computes carries a fact ID (period
  facts, or turn-scoped `fact:q_<hash>:<name>`); the answer cites with `[[…]]` markers rendered as
  chips that open the fact, finding, document page or match.
- **AC-011-3** The grounding guard runs on every answer; on failure the answer becomes the tool
  results as a table with "I could not phrase this safely" (`grounding: TEMPLATE`).
- **AC-011-4** Answers can include `table` and `chart` parts (`MONEY_FLOW`, `MONTHLY_IN_OUT`,
  `CATEGORY_BREAKDOWN`) rendered with the dashboard's components.
- **AC-011-5** Out-of-scope or write requests ("pay this invoice", "delete March") are declined with
  what the user can do instead; no tool can change data.

### US-011-2: Find words in documents and help

- **AC-011-6** After reading, the document workflow writes `retrievalChunks` (page text or 50-row
  ledger blocks, ≤ 2,000 characters, `gemini-embedding-001` 768 dimensions); deleting a document
  deletes its chunks; `tools/knowledge/build.py` writes `knowledgeChunks` from the policy files, the
  check catalog and help pages.
- **AC-011-7** `search_documents(query, docType?, month?)` and `search_knowledge(query)` use Firestore
  `find_nearest` (cosine, top 8) and return passages with document and page references, framed as
  untrusted text in the prompt.

### US-011-3: Remember my preferences, nothing else

- **AC-011-8** Sessions use `VertexAiSessionService` (`AGENT_SESSIONS_ID`) and memories
  `VertexAiMemoryBankService` (`MEMORY_BANK_ID`), with `user_id = "{orgId}:{uid}"`;
  `PreloadMemoryTool` loads memories at the start of a turn; new events go to Memory Bank with
  `add_events_to_memory` after each turn.
- **AC-011-9** Memory generation uses the custom topics of `infra/memory-topics.yaml` (display
  preferences, fiscal calendar, account nicknames, counterparties the user calls related or trusted);
  no figures, findings or document content are stored as memories (asserted in the DeepEval suite).
- **AC-011-10** `GET /api/assistant/memories` lists them; `DELETE` forgets them all;
  `ASSISTANT_MEMORY=off` keeps the assistant working with sessions only.

### US-011-4: The screen

- **AC-011-11** `/assistant` shows threads and a chat with suggested questions for the current
  period; answers stream (`text/event-stream`); on phones the chat is full screen with the composer
  above the keyboard; a "Remembered" panel shows and clears memories.
- **AC-011-12** "Ask about this" buttons on the dashboard, a month and a finding open a thread scoped
  to it.

### US-011-5: Measured

- **AC-011-13** `backend/evals/assistant/` runs the 20 cases of [`docs/15`](../../15-testing-and-evaluation.md)
  §5.1 with DeepEval (Gemini judge on Agent Platform) and the same cases as an ADK eval set; thresholds
  as in §5.1; results in the eval report.

## Out of scope

Actions from chat, voice, other languages, sharing threads, RAG Engine (an alternative behind
`search_documents` later).
