# Tasks 011 — Finance Assistant

## Phase 1 — Platform

- [ ] **T011-01** Spike S5; create the Memory Bank (with memory topics) and the Sessions container; record findings in `docs/02`. (AC-011-8, AC-011-9)
- [ ] **T011-02** Embedder, retrieval chunk writing and deletion, knowledge build; vector indexes deployed. (AC-011-6, AC-011-7)

## Phase 2 — Agent

- [ ] **T011-03** **TDD** read-only tools with fact IDs and server-set scope (foreign `orgId` impossible). (AC-011-1, AC-011-2)
- [ ] **T011-04** Agent, prompt and runner with sessions and memory; quota and tool-call cap. (AC-011-1, AC-011-8)
- [ ] **T011-05** **TDD** grounding on answers incl. turn-scoped facts; template fallback; decline writes. (AC-011-3, AC-011-5)

## Phase 3 — API and UI

- [x] **T011-06** Assistant routes with SSE; memories list and purge. (AC-011-10)
- [x] **T011-07** `AssistantPage`, `AnswerParts`, "Ask about this". (AC-011-4, AC-011-11, AC-011-12)


## Phase 4 — Evaluation and close

- [ ] **T011-08** DeepEval suite and ADK eval set; add E-AST to the report. (AC-011-13)
- [ ] **T011-09** Update `docs/20-implementation-status.md`.
