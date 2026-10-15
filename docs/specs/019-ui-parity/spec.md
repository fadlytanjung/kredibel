# Spec 019 — Current UI and mock parity

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 maintenance, requested 15 October 2026 |
| **Owner role** | C + D |
| **Depends on** | 001, implemented portions of 003, 007, 009, 010, 011, 013, 018 |
| **Requirements** | FR-070, NFR-08, NFR-11, NFR-13, NFR-14 |

## Summary

The team needs mocks that describe the implemented workspace, plus clearly identified designs for
features still pending. Recent work changed the dashboard order, assistant history/composer, P&L
flow, document evidence and review corrections without consistently updating the mocks. Refresh
those references and add executable parity checks. This maintains existing P0 scope; it does not
promote planned P1 screens to completed features.

## User stories

### US-019-1: Review the current product

- **AC-019-1** Given the mock index, when a screen is opened, then its implementation status and
  corresponding route are identifiable. Planned clients/suppliers, Labels and Runs remain marked
  as design-only. Implemented screens cannot silently use a deprecated layout.
- **AC-019-2** Given dashboard and assistant screens, when viewed at 390/834/1440 px, then mock and
  application agree on main section order, navigation, chart choices and interaction states.
  The assistant has a left history rail on wide screens, a history drawer on phones, welcome
  prompts, conversation and activity states, and an accessible composer.
- **AC-019-3** Given document, month and review workflows, when inspecting their mocks, then the
  references include implemented ledger metadata, document-first reconciliation, match/source
  inspection and value corrections. Unimplemented tabs/actions are identified as planned.

### US-019-2: Prevent another silent drift

- **AC-019-4** Given an affected UI change, when checked, then generated mock freshness and relevant
  mock/application parity tests pass, with reviewed screenshots and externalized UI words. Screen
  controls remain usable at 360/1600 px and keyboard users can inspect the same content.
- **AC-019-5** Given task checkboxes and implementation status, when audited against code and tests,
  then incomplete acceptance criteria remain open, with their task IDs and next dependencies.
  Historical session summaries and commits alone never establish completion or deployment.

## Out of scope

Building the clients/suppliers, Labels or Runs features; completing the assistant managed platform;
changing accounting policy or posting ledgers; deployment. Core backend gaps retain their original
spec/task ownership and are implemented in separate changes.

## Edge cases

Empty, loading and failed queries must not pretend to have populated synthetic data. A mock is
synthetic, never a screenshot of real customer documents. Read-only roles have no write affordance.
