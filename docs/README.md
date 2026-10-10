# Kredibel documentation

Specifications are the source of truth: code implements them, and both change together.

## Reading order

**For the team review (today):** 01 → 01a → 03 → 19 → 05 → 06. **What changed in this round:** ADR-010, ADR-011, ADR-012, then 07 §5–§6, 21 §3, specs 013 and 014.
**For a coding agent starting a spec:** `AGENTS.md` → 00 → the spec folder → the docs it links.

| # | Document | Answers |
|---|---|---|
| 00 | [Constitution](00-constitution.md) | The principles every change is checked against |
| 01 | [Brainstorm & decision](01-brainstorm-and-decision.md) | Which idea, why, what's out of scope, the name |
| 01a | [Concept deep-dive](01a-concept-deep-dive.md) | The chosen idea in depth: problem anatomy, agent crew, scenarios, differentiation, business model, roadmap, judges' FAQ |
| 02 | [Research](02-research.md) | Competition facts, Google Cloud facts, evidence, spikes |
| 03 | [PRD](03-prd.md) | Users, journeys, P0/P1/P2 scope, FR/NFR |
| 04 | [Requirements traceability](04-requirements-traceability.md) | FR → spec → test; judging criteria → evidence |
| 05 | [Architecture](05-architecture.md) | Containers, flows, lifecycle, regions, limits |
| 06 | [Agent design](06-agent-design.md) | ADK workflow, nodes, LLM contracts, prompts, guardrails, assistant |
| 07 | [Document intelligence](07-document-intelligence.md) | Page split, classification, adaptive reading (AI reader + witness), verification, provenance |
| 08 | [Risk engine](08-risk-engine.md) | Check catalog, verdicts, taxonomy, metrics, reconciliation, scorecard |
| 09 | [Data model](09-data-model.md) | Firestore collections, GCS layout, indexes, rules |
| 10 | [API contract](10-api-contract.md) | Endpoints, errors, payloads (YAML in `contracts/`) |
| 11 | [Frontend](11-frontend.md) | Structure, routes, screens, realtime, states |
| 12 | [Design system](12-design-system.md) | Tokens, type, components, content style |
| 13 | [Design patterns & conventions](13-design-patterns-and-conventions.md) | Layout, layers, patterns, coding and git conventions |
| 14 | [Security & compliance](14-security-and-compliance.md) | Threat model, LLM risks, IAM, data protection |
| 15 | [Testing & evaluation](15-testing-and-evaluation.md) | Test layers, ground truth, eval suites |
| 16 | [Infrastructure & deployment](16-infrastructure-and-deployment.md) | Bootstrap, Cloud Run, env vars, CI/CD, runbook |
| 17 | [Observability](17-observability.md) | Logs, traces, metrics, alerts |
| 18 | [Synthetic data](18-synthetic-data.md) | Generator, fictional world, tamper techniques, scenarios |
| 19 | [Delivery plan](19-delivery-plan.md) | Roles, day-by-day plan, cut line, definition of done |
| 20 | [Implementation status](20-implementation-status.md) | What is actually built |
| 21 | [Cost analysis & database options](21-cost-analysis.md) | What it costs, extraction strategies compared, why Firestore over Cloud SQL, cost guardrails |
| — | [Glossary](glossary.md) | Terms |
| — | [ADRs](adr) | Decisions and their trade-offs |

## Diagrams

Two kinds of diagram live in these docs:

- **Mermaid** blocks inside the markdown, for flows that change with the text (sequences, state
  machines, ER, charts). They render in GitHub, VS Code and Antigravity previews.
- **draw.io** files in [`diagrams/`](diagrams/), saved as `.drawio.svg`: a normal SVG image with the
  editable diagram embedded. Open one in VS Code with the draw.io extension to edit it; save, and the
  image in every doc updates. Use them for pictures Mermaid draws poorly: cloud architecture with
  product icons, swimlanes, annotated trust boundaries, evidence lineage and UI wireframes.

| Diagram | Shows | Used in |
|---|---|---|
| [`gcp-architecture`](diagrams/gcp-architecture.drawio.svg) | Google Cloud services, regions, the numbered path of one analysis | README, 05 §7 |
| [`analysis-swimlane`](diagrams/analysis-swimlane.drawio.svg) | Who does what from upload to decision | 05 §5.2 |
| [`trust-boundaries`](diagrams/trust-boundaries.drawio.svg) | Boundaries, controls C1–C9, the tests that prove them | 14 §1 |
| [`evidence-lineage`](diagrams/evidence-lineage.drawio.svg) | One printed value traced to the analyst's decision (S2) | 01a §5, 07 §7 |
| [`ui-case-workspace`](diagrams/ui-case-workspace.drawio.svg) | Wireframe: case workspace, Overview tab, decision panel | 11 §6.3 |
| [`ui-evidence-viewer`](diagrams/ui-evidence-viewer.drawio.svg) | Wireframe: evidence viewer drawer | 11 §6.7 |
| [`extraction-adaptive`](diagrams/extraction-adaptive.drawio.svg) | Adaptive reading: page split, triage, AI reader, witness, verifier, escalation, with costs | 07 §7 |
| [`ui-applicant-onboarding`](diagrams/ui-applicant-onboarding.drawio.svg) | Wireframe: new case wizard, applicant step (company) | 11 §6.2 |
| [`ui-applicant-profile`](diagrams/ui-applicant-profile.drawio.svg) | Wireframe: applicant tab with AI suggestions and counterparties | 11 §6.5a |
| [`ui-plans`](diagrams/ui-plans.drawio.svg) | Wireframe: plan & usage, free trial and coming-soon tiers | 11 §6.0 |

Rules: one diagram per file; keep names, codes and values identical to the specs; synthetic names
only; when a change alters what a diagram shows, update the diagram in the same commit.

## Feature specs and submission

| Folder | Content |
|---|---|
| [`specs/`](specs/README.md) | 14 feature specs (`spec.md` → `plan.md` → `tasks.md`), build order and dependency graph |
| [`submission/`](submission/) | Proposal draft, 3-minute demo script, submission checklist |

## Decisions (ADRs)

| ADR | Decision |
|---|---|
| [001](adr/ADR-001-adk-graph-workflows.md) | ADK 2.x workflows for orchestration |
| [002](adr/ADR-002-cloud-run-not-agent-runtime.md) | Run agents inside Cloud Run, not Agent Runtime |
| [003](adr/ADR-003-firestore-system-of-record.md) | Firestore as the system of record |
| [004](adr/ADR-004-dual-extraction-consensus.md) | Two independent readers + consensus (readers revised by 010) |
| [005](adr/ADR-005-deterministic-scoring-llm-explains.md) | Deterministic scoring; models explain |
| [006](adr/ADR-006-async-jobs-cloud-tasks.md) | Asynchronous runs through Cloud Tasks |
| [007](adr/ADR-007-hitl-state-machine.md) | Human-in-the-loop as a case state machine |
| [008](adr/ADR-008-same-origin-spa-firebase-auth.md) | Same-origin SPA on Cloud Run + Firebase Auth |
| [009](adr/ADR-009-regions-and-data-residency.md) | Regions and the data-residency path |
| [010](adr/ADR-010-adaptive-extraction-ai-reader-and-witness.md) | Adaptive extraction: one AI reader and a deterministic witness per page (supersedes part of 004) |
| [011](adr/ADR-011-workspaces-and-plans-free-trial-only.md) | Workspaces and plans: free trial only, no billing |
| [012](adr/ADR-012-applicant-profile-with-ai-suggestions.md) | Applicant profile, filled by the analyst and suggested by the AI |

## Machine-readable contracts

| File | Purpose |
|---|---|
| [`contracts/openapi.yaml`](../contracts/openapi.yaml) | REST API (OpenAPI 3.1) |
| [`contracts/firestore.rules`](../contracts/firestore.rules) | Firestore security rules |
| [`contracts/firestore.indexes.json`](../contracts/firestore.indexes.json) | Composite indexes |
| [`contracts/policy/scorecard.v1.yaml`](../contracts/policy/scorecard.v1.yaml) | Scorecard, grades, hard stops, conditions |
| [`contracts/policy/categorization-rules.v1.yaml`](../contracts/policy/categorization-rules.v1.yaml) | Keyword categorization rules |
| [`contracts/policy/forensics.v1.yaml`](../contracts/policy/forensics.v1.yaml) | Enabled checks and thresholds |
| [`contracts/plans.v1.yaml`](../contracts/plans.v1.yaml) | Plans (free trial, coming-soon tiers), limits, UI languages, policy override bounds |
