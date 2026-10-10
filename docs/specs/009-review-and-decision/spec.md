# Spec 009 — Review & Decision

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 (P1 section at the end) |
| **Owner role** | C: Frontend (+ B/D for the API) |
| **Depends on** | 008 (API data), 003 (workspace shell) |
| **Requirements** | FR-040 … FR-046, NFR-08, P0-13, P0-14, P0-15; P1: FR-054, P1-09, P1-10 |
| **Design** | [`docs/11`](../../11-frontend.md) §6, [`docs/12`](../../12-design-system.md), [`docs/05`](../../05-architecture.md) §6 |

## Summary

The analyst's workspace after analysis: overview, applicant (built in spec 014), findings, evidence
viewer, cash flow, reconciliation, memo, activity, and a decision panel whose rules are enforced by the
server's state machine. The case header shows the applicant's name and type; the evidence viewer shows
the two readings of a value as "Gemini (page image)" and "PDF text layer" or "OCR".

## User stories

### US-009-1: Understand the case at a glance

- **AC-009-1** Overview shows score gauge + grade, recommendation, hard stops with reasons, max
  supportable vs requested amount, six key metric tiles with formula popovers, a document integrity
  strip, and the top 3 findings.
- **AC-009-2** On S2 the overview shows `DECLINE`, hard stop `TAMPERED_DOCUMENT`, and the March
  statement chip as Tampered.

### US-009-2: Work through findings

- **AC-009-3** Findings are grouped by severity then document, filterable by severity, category,
  document and status.
- **AC-009-4** Acknowledge sets `ACKNOWLEDGED`; Dismiss requires a reason (≥ 10 chars); both are
  recorded as events with the actor (`PATCH …/findings/{id}`).

### US-009-3: See the evidence

- **AC-009-5** Opening a finding shows the page with highlighted boxes (severity colour + numbered
  marker), the finding's facts (e.g. expected vs printed), both readings' raw values (AI reader and witness) when available,
  related findings on the same row, and acknowledge/dismiss actions.
- **AC-009-6** Keyboard: `j`/`k` next/previous finding, `+`/`-` zoom, `Esc` close; deep link
  `/cases/:id/evidence/:findingId` opens directly.
- **AC-009-7** Evidence without a bbox shows the page with "Exact location not available".

### US-009-4: Cash flow and reconciliation

- **AC-009-8** Cash flow tab: monthly inflow/outflow bars + ADB line + negative-day markers, a "view as
  table" alternative, category breakdown, and the filterable transaction table; clicking a row opens the
  evidence viewer at that row.
- **AC-009-9** Reconciliation tab: invoiced vs matched summary and the invoice table with statuses and
  links to matched transactions; unmatched rows link to their R01 finding.

### US-009-5: Read the memo

- **AC-009-10** Memo sections render as safe markdown; citation markers become chips (fact popover,
  finding → evidence viewer, doc page → viewer); grounding badge Verified / Unverified with problems.

### US-009-6: Decide

- **AC-009-11** `POST …/decision` enforces the state-machine guards of [`docs/05`](../../05-architecture.md) §6:
  approve blocked while a CRITICAL finding is OPEN (`409 OPEN_CRITICAL_FINDINGS` with IDs); approving
  against `DECLINE` or a hard stop requires at least `risk_lead` (`risk_lead` or `admin`; else `403 ROLE_REQUIRED`) and a reason; `DECLINE`,
  `REQUEST_INFO`, `ESCALATE` require a reason (`422 REASON_REQUIRED`); invalid transitions →
  `409 INVALID_TRANSITION`.
- **AC-009-12** The decision panel mirrors these rules (disabled buttons with reasons, role hints) and
  still handles the server errors.
- **AC-009-13** A recorded decision updates case status and `decision`, marks the memo `FINAL`, and
  appends `DECISION_RECORDED` in the same transaction; the panel then shows outcome, who, when, reason.
- **AC-009-14** `ESCALATED` cases can only be decided by a `risk_lead` or `admin`.

### US-009-7: Audit

- **AC-009-15** Activity tab lists events newest first with actor, type and details.

## P1 section

- **AC-009-16 (FR-054)** Edit memo sections; save → `PUT …/memo` re-runs the guard; status `EDITED`;
  `MEMO_EDITED` event.
- **AC-009-17 (P1-10)** Re-categorize a transaction → `categorizedBy: ANALYST`, event, banner
  "Analysis out of date. Re-run".
- **AC-009-18 (P1-09)** On `REQUEST_INFO`, `POST …/info-request/draft` returns a drafted
  information-request letter (Gemini, from findings and missing coverage) shown for copy; it lists
  specific documents and reasons, no internal codes, and nothing is sent automatically.
