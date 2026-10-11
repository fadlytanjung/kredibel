# Plan 011 — Finance Assistant

## Backend

| File | Content |
|---|---|
| `agents/assistant.py` | `finance_assistant` Agent, `Runner` with `VertexAiSessionService` and `VertexAiMemoryBankService` ([`docs/06`](../../06-agent-design.md) §10) |
| `agents/tools/finance_tools.py` | read-only tools; each returns values with fact IDs; scope from `tool_context.state` set by the server |
| `agents/prompts/finance_assistant.md` | instruction: tools for numbers, retrieval for words, cite everything, decline writes |
| `adapters/vertex_embedder.py` | `gemini-embedding-001`, 768 dimensions, batch embedding |
| `agents/nodes/doc_nodes.py` | `write_retrieval_chunks` after `verify_pages` / `parse_ledger` (flag `FEATURE_ASSISTANT`) |
| `tools/knowledge/build.py` | split policy and help into passages, embed, upsert `knowledgeChunks` |
| `services/assistant_service.py` | threads, ask (quota, run, grounding guard, parts), SSE streaming, memories list and purge |
| `api/assistant.py` | routes of [`docs/10`](../../10-api-contract.md) §2.8 |
| `backend/scripts/create_assistant_memory.py`, `infra/memory-topics.yaml` | Memory Bank and Sessions container, configuration ([`docs/16`](../../16-infrastructure-and-deployment.md) §3) |
| `backend/evals/assistant/` | `assistant_cases.yaml`, `test_assistant_deepeval.py`, `*.evalset.json` |

## Frontend

| File | Content |
|---|---|
| `pages/AssistantPage.tsx` | threads, chat, suggested questions, remembered panel |
| `features/assistant/AnswerParts.tsx` | text with citation chips, tables, charts (reusing `MoneyFlow`, `KpiCard` charts) |
| `features/assistant/AskAboutThis.tsx` | scoped thread from dashboard, month, finding |

## Spikes

- **S5** Sessions and Memory Bank from Cloud Run without deployed agent code (one instance or two);
  region; latency of `PreloadMemoryTool`; memory generation with custom topics.

## Constitution check

P2 ✔ (numbers from tools) · P3 ✔ (citations, guard) · P4 ✔ (retrieved text untrusted) · P9 ✔ (P1 only)
