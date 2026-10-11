# Spec 008 — Fraud Risk and Explanations

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 |
| **Owner role** | B: Risk engine (levels) + A: Agents (explainer, grounding guard) + C (risk pages) |
| **Depends on** | 006, 007 |
| **Requirements** | FR-041, FR-042, FR-043, P0-11, P0-13, NFR-08 |
| **Design** | [`docs/08`](../../08-risk-engine.md) §8; [`docs/06`](../../06-agent-design.md) §5, §5.1; `contracts/policy/risk.v1.yaml` |

## Summary

Every document and every month gets a **fraud risk level** (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
computed by rules from its findings, with the reasons listed. Gemini writes a short explanation and
orders the **next steps** from a fixed catalog; a grounding guard makes sure every number it writes
exists as a fact or finding, and falls back to template text if not. The **Risk** page and the
evidence viewer let a person see why, look at the page, and acknowledge or dismiss.

## User stories

### US-008-1: A risk level with reasons

- **AC-008-1** Document level and month level follow [`docs/08`](../../08-risk-engine.md) §8 and
  `risk.v1.yaml`; any `TAMPERED` document makes its month `CRITICAL`; `X08` or `D07` open → at least
  `HIGH`; the level lists the finding IDs behind it.
- **AC-008-2** A risk score 0–100 is stored for sorting only; the UI shows the level, never the score.
- **AC-008-3** Dismissed findings no longer raise a level; acknowledged ones still do.

### US-008-2: An explanation I can trust

- **AC-008-4** `explain_month` receives the month's level, its findings as facts, its figures and the
  catalog's next steps for those codes, and returns a summary (≤ 3 sentences), ordered next steps and
  one plain-language explanation per HIGH or CRITICAL finding, with `[[…]]` citation markers.
- **AC-008-5** The grounding guard ([`docs/06`](../../06-agent-design.md) §5.1) rejects a number that
  is not a cited fact or finding value and a marker that does not resolve; one retry with the
  problems; then the template text (`grounding: TEMPLATE`). The UI labels "Written by Gemini · figures
  verified by Kredibel" or "Standard wording".
- **AC-008-6** The explainer is skipped when the month's facts and findings hash is unchanged.

### US-008-3: The Risk page and the evidence viewer

- **AC-008-7** `/risk` lists open findings, most severe first, grouped by month, with filters
  (severity, month, document, code, status) and the level of each month at the top.
- **AC-008-8** `/risk/:findingId` opens the **evidence viewer**: the page zoomed to the highlighted
  value (the lamp), both readings of each value involved, the calculation behind the finding (e.g.
  `41,250,000 + 7,250,000 ≠ 42,500,000`), the explanation and next steps. On phones the page is shown
  above the finding with a magnifier crop; on desktop side by side.
- **AC-008-9** `PATCH /api/findings/{id}`: acknowledge, or dismiss with a reason (required for HIGH
  and CRITICAL, ≥ 10 characters); both audited; the month re-scores.
- **AC-008-10** Severity is shown with colour **plus** icon **plus** text (NFR-08).

### US-008-4: Scenario outcomes

- **AC-008-11** S1: every month `LOW`. S2: March `CRITICAL` with next step "Download the March
  statement again from internet banking and upload it". S4: May `HIGH` with "Confirm the new account
  with the supplier using a phone number you already have".

## Out of scope

The review queue (009), dashboard alerts (010), the assistant (011), Model Armor `S01` (015).
