# Spec 011 — Case Assistant (P1)

| | |
|---|---|
| **Status** | Ready (after 010 ①–③, or in parallel if a person is free) |
| **Priority** | P1 |
| **Owner role** | A: Agents (+ C for the drawer) |
| **Depends on** | 008, 009 |
| **Requirements** | FR-053, P1-04 |
| **Design** | [`docs/06`](../../06-agent-design.md) §9 |

## Summary

An ADK conversational agent that answers an analyst's questions about **one** case using read-only
tools, citing facts and findings, with conversation memory in Agent Platform Sessions.

## User stories

### US-011-1: Ask about the case

- **AC-011-1** In a case with a completed run, `POST …/assistant/messages {text}` returns a reply with
  citation markers that resolve to facts, findings or document pages of that case; the UI renders them
  as chips.
- **AC-011-2** "Why is the March statement flagged?" on S2 → calls `list_findings` and/or `get_finding`
  and cites the A01 finding.
- **AC-011-3** "Which invoices were never paid?" on S3 → calls `get_reconciliation(status=UNMATCHED)` and
  lists the 5 invoices with citations.
- **AC-011-4** "What drives the DSCR?" → `explain_metric("dscr_proxy")` and cites the inputs.

### US-011-2: Stay in bounds

- **AC-011-5** Tools read `orgId`/`caseId` only from session state set by the server; a question
  mentioning another case ID cannot access it (test).
- **AC-011-6** Asked to approve or change data, the assistant declines and points to the decision panel;
  no write tools exist.
- **AC-011-7** Before a run exists → `409 ANALYSIS_NOT_READY`.

### US-011-3: Remember the conversation

- **AC-011-8** Follow-up questions use prior turns (session per user + case in Agent Platform Sessions;
  in-memory locally); history is shown when reopening the drawer (`GET …/assistant/messages`).

### US-011-4: Measured

- **AC-011-9** An ADK eval set with ≥ 8 cases over S1–S3 runs via `adk eval`; trajectory and citation
  checks reported in the eval report (target ≥ 0.9).
