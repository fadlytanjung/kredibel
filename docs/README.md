# Kredibel documentation

Specifications are the source of truth: code implements them, and both change together.

## Reading order

**For the team review (today):** ADR-015 → 01a → 03 → 19 → 05 → 06 → 08. **What changed in this round:** the scope moved from loan review to a finance workspace that checks a business's own books ([ADR-015](adr/ADR-015-scope-finance-workspace-not-loan-review.md)): duplicates, reconciliation in any upload order, a review queue, fraud risk, a dashboard with a money-flow Sankey, the Finance Assistant ([ADR-014](adr/ADR-014-finance-assistant-tools-rag-memory.md)), a new design and logo, and versioned data ([ADR-013](adr/ADR-013-versioned-documents-and-forward-migrations.md), [`22`](22-data-migrations.md)). **Added 11 Oct:** labels people confirm or correct, with IFRS or US GAAP categories ([ADR-016](adr/ADR-016-human-verified-labels-and-learning-loop.md)), and LangSmith-style run history on Google Cloud ([ADR-017](adr/ADR-017-agent-observability-on-google-cloud.md)).
**For a coding agent starting a spec:** `AGENTS.md` → 00 → the spec folder → the docs it links.

| # | Document | Answers |
|---|---|---|
| 00 | [Constitution](00-constitution.md) | The principles every change is checked against |
| 01 | [Brainstorm & decision](01-brainstorm-and-decision.md) | Which idea, why, what's out of scope, the name |
| 01a | [Concept deep-dive](01a-concept-deep-dive.md) | The product in depth: problem, users, the product end to end, hero scenarios, differentiation, roadmap, pitch kit |
| 02 | [Research](02-research.md) | Competition facts, Google Cloud facts, evidence, spikes |
| 03 | [PRD](03-prd.md) | Users, journeys, P0/P1/P2 scope, FR/NFR |
| 04 | [Requirements traceability](04-requirements-traceability.md) | FR → spec → test; judging criteria → evidence |
| 05 | [Architecture](05-architecture.md) | Containers, flows, month lifecycle, regions, limits |
| 06 | [Agent design](06-agent-design.md) | Document and month workflows, nodes, LLM contracts, grounding guard, prompts, guardrails, Finance Assistant |
| 07 | [Document intelligence](07-document-intelligence.md) | Upload and exact duplicates, page split, classification, adaptive reading (AI reader + witness), ledger import, verification, provenance |
| 08 | [Risk engine](08-risk-engine.md) | Duplicates, check catalog, verdicts, categories, counterparties, month figures, money flow, reconciliation, review items, risk levels |
| 09 | [Data model](09-data-model.md) | Firestore collections, GCS layout, indexes, rules |
| 10 | [API contract](10-api-contract.md) | Endpoints, errors, payloads (YAML in `contracts/`) |
| 11 | [Frontend](11-frontend.md) | Information architecture, routes, screens, responsive rules, realtime, states |
| 12 | [Design system](12-design-system.md) | Brand and logo, tokens, type, layout, components, charts, content style, quality gates |
| 13 | [Design patterns & conventions](13-design-patterns-and-conventions.md) | Layout, layers, patterns, coding and git conventions |
| 14 | [Security & compliance](14-security-and-compliance.md) | Threat model, LLM risks, IAM, data protection |
| 15 | [Testing & evaluation](15-testing-and-evaluation.md) | Test layers, UI gates, ground truth, eval suites, DeepEval for the assistant |
| 16 | [Infrastructure & deployment](16-infrastructure-and-deployment.md) | Bootstrap, Cloud Run, env vars, CI/CD, runbook |
| 17 | [Observability](17-observability.md) | Logs, ADK traces, metrics, run graph, alerts |
| 18 | [Synthetic data](18-synthetic-data.md) | Generator, fictional books, tamper and duplicate techniques, scenarios S1–S6 |
| 19 | [Delivery plan](19-delivery-plan.md) | Roles, day-by-day plan, cut line, definition of done |
| 20 | [Implementation status](20-implementation-status.md) | What is actually built |
| 21 | [Cost analysis & database options](21-cost-analysis.md) | What it costs per document, half-year and question; reading strategies compared; why Firestore over Cloud SQL; cost guardrails |
| 22 | [Data migrations](22-data-migrations.md) | Versioned documents, upcasters, forward-only migrations, backups, portability |
| 23 | [How the agents work, and how to trace them](23-agents-and-tracing-guide.md) | ADK for LangGraph and LangSmith users: workflows, runs, the dev UI (`make dev-agents`), Cloud Trace |
| — | [Glossary](glossary.md) | Terms |
| — | [ADRs](adr) | Decisions and their trade-offs |

## Diagrams

Two kinds of diagram live in these docs:

- **Mermaid** blocks inside the markdown, for flows that change with the text (sequences, state
  machines, ER, charts). They render in GitHub, VS Code and Antigravity previews.
- **draw.io** files in [`diagrams/`](diagrams/), saved as `.drawio.svg`: a normal SVG image with the
  editable diagram embedded. Open one in VS Code with the draw.io extension to edit it; save, and the
  image in every doc updates. Use them for pictures Mermaid draws poorly: cloud architecture with
  product icons, swimlanes, annotated trust boundaries and evidence lineage. They use the colours of
  [`contracts/design/tokens.json`](../contracts/design/tokens.json).
- **Screen mocks** in [`../design/mocks/`](../design/mocks/index.html): responsive HTML built from the
  design tokens and generated by `tools/design/mocks/` (`make mocks`), with screenshots at 390, 834
  and 1440 px in [`assets/mocks/`](assets/mocks/) (`make mock-shots`). The screen rules are written
  in [`11`](11-frontend.md) §6; the flows between screens are Mermaid diagrams in
  [`11`](11-frontend.md) §4.3–§5.3. The mocks link to each other, so they also work as a clickable
  prototype: open [`dashboard`](../design/mocks/dashboard.html) and follow any link.

| Diagram | Shows | Used in |
|---|---|---|
| [`gcp-architecture`](diagrams/gcp-architecture.drawio.svg) | Google Cloud services, regions, the numbered path of one upload | README, 05 §7 |
| [`analysis-swimlane`](diagrams/analysis-swimlane.drawio.svg) | Who does what from upload to a reconciled month, and the fix loop | 05 §5.2 |
| [`trust-boundaries`](diagrams/trust-boundaries.drawio.svg) | Boundaries, controls C1–C11, the tests that prove them | 14 §1 |
| [`evidence-lineage`](diagrams/evidence-lineage.drawio.svg) | One printed value traced to the month's risk level (S2) | 07 §7 |
| [`extraction-adaptive`](diagrams/extraction-adaptive.drawio.svg) | Adaptive reading: page split, triage, AI reader, witness, verifier, escalation, with costs | 07 §7 |
| [`screen-flow`](diagrams/screen-flow.drawio.svg) | The screen mocks as thumbnails, linked by what a person clicks | 11 §4.3 |

| Screen mock | Shows | Used in |
|---|---|---|
| [`onboarding`](../design/mocks/onboarding.html) | Myself or a company, the free trial, the brand panel | 11 §6.1 |
| [`dashboard`](../design/mocks/dashboard.html) | Status sentence, figures, Needs you, Risk, then full-width charts by IFRS or US GAAP (money flow by statement line, money in and out by month, cash-flow statement), months as binder tabs | 11 §6.2 |
| [`documents`](../design/mocks/documents.html) | Upload tray (exact copy, held copy, reading, new ledger layout) and the library | 11 §6.3 |
| [`month`](../design/mocks/month.html) | March 2026: figures, the critical explanation, bank lines with match reasons | 11 §6.4 |
| [`review`](../design/mocks/review.html) | The review queue and the fix panel | 11 §6.5 |
| [`evidence-viewer`](../design/mocks/evidence-viewer.html) | The lamp, calculation, two readings; magnifier on phones | 11 §6.6 |
| [`assistant`](../design/mocks/assistant.html) | Finance Assistant with a chart in the answer and what is remembered (P1) | 11 §6.8 |
| [`plan-usage`](../design/mocks/plan-usage.html) | Trial, usage meters, coming-soon plans and features | 11 §6.9 |
| [`risk`](../design/mocks/risk.html) | Findings grouped by month with severity, code and status | 11 §6.7 |
| [`clients`](../design/mocks/clients.html) | Clients and suppliers with shares; a new supplier account flagged | 11 §6.7 |
| [`labels`](../design/mocks/labels.html) | Labels to check, per-page types, extraction files, the label panel (P1) | 11 §6.11 |
| [`runs`](../design/mocks/runs.html) | Runs, span waterfall and one model call inspected (P1) | 11 §6.12 |
| [`brand`](../design/mocks/brand.html) | The logo idea (a k that has been checked), construction, versions, colours, misuse | 12 §9 |

Rules: one diagram per file; keep names, codes and values identical to the specs; synthetic names
only; when a change alters what a diagram shows, update the diagram in the same commit.

## Feature specs and submission

| Folder | Content |
|---|---|
| [`specs/`](specs/README.md) | 15 feature specs (`spec.md` → `plan.md` → `tasks.md`), build order and dependency graph |
| [`submission/`](submission/) | Proposal draft, 3-minute demo script, submission checklist |

## Decisions (ADRs)

| ADR | Decision |
|---|---|
| [001](adr/ADR-001-adk-graph-workflows.md) | ADK 2.x workflows for orchestration |
| [002](adr/ADR-002-cloud-run-not-agent-runtime.md) | Run agents inside Cloud Run, not Agent Runtime |
| [003](adr/ADR-003-firestore-system-of-record.md) | Firestore as the system of record |
| [004](adr/ADR-004-dual-extraction-consensus.md) | Two independent readers + consensus (readers revised by 010) |
| [005](adr/ADR-005-deterministic-scoring-llm-explains.md) | Deterministic checks and risk levels; models read and explain |
| [006](adr/ADR-006-async-jobs-cloud-tasks.md) | Asynchronous runs through Cloud Tasks |
| [007](adr/ADR-007-hitl-review-queue.md) | Human-in-the-loop as a review queue, not paused workflows |
| [008](adr/ADR-008-same-origin-spa-firebase-auth.md) | Same-origin SPA on Cloud Run + Firebase Auth (hosting part superseded by 018) |
| [009](adr/ADR-009-regions-and-data-residency.md) | Regions and the data-residency path |
| [010](adr/ADR-010-adaptive-extraction-ai-reader-and-witness.md) | Adaptive extraction: one AI reader and a deterministic witness per page (supersedes part of 004) |
| [011](adr/ADR-011-workspaces-and-plans-free-trial-only.md) | Workspaces and plans: free trial only, no billing |
| [012](adr/ADR-012-profile-with-ai-suggestions.md) | Workspace profile, filled by the user and suggested by the AI |
| [013](adr/ADR-013-versioned-documents-and-forward-migrations.md) | Versioned documents and forward-only migrations |
| [014](adr/ADR-014-finance-assistant-tools-rag-memory.md) | Finance Assistant: tools first, Firestore retrieval, Memory Bank for preferences |
| [015](adr/ADR-015-scope-finance-workspace-not-loan-review.md) | Scope: a finance workspace that checks your books, not loan review |
| [016](adr/ADR-016-human-verified-labels-and-learning-loop.md) | Human-verified labels and the learning loop (IFRS or US GAAP; examples now, tuning later) |
| [017](adr/ADR-017-agent-observability-on-google-cloud.md) | Agent observability on Google Cloud instead of LangSmith |
| [018](adr/ADR-018-firebase-hosting-in-front-of-cloud-run.md) | Firebase Hosting serves the SPA and rewrites `/api` to Cloud Run (supersedes the hosting part of 008) |
| [019](adr/ADR-019-one-component-stylesheet-for-mocks-and-app.md) | `kit.css` and the mock icon set are the component stylesheet and icons of the app too (supersedes the Tailwind rebuild rule of 12 §0) |
| [020](adr/ADR-020-workspace-currency-chosen-at-onboarding.md) | One currency per workspace (IDR, MYR, SGD, JPY, USD), chosen at onboarding and fixed afterwards; hundredths in Firestore for every currency |
| [021](adr/ADR-021-kredibel-firestore-database.md) | Kredibel's own Firestore database `kredibel` in the shared project; firebase.json targets only it |
| [022](adr/ADR-022-real-documents-in-production.md) | Real documents in production with real-data controls always on; synthetic data for tests (amends P8) |
| [023](adr/ADR-023-parse-extract-ground.md) | Parse pages into layout chunks (text layer or Document AI OCR), extract with Gemini from image plus chunks with citations, ground every value in code |
| [024](adr/ADR-024-runtime-configuration-in-secret-manager.md) | Production configuration is one Secret Manager secret (`kredibel-env`), mounted as `/secrets/.env` for both services and read by the build for the SPA's Firebase config |

## Machine-readable contracts

| File | Purpose |
|---|---|
| [`contracts/openapi.yaml`](../contracts/openapi.yaml) | REST API (OpenAPI 3.1) |
| [`contracts/firestore.rules`](../contracts/firestore.rules) | Firestore security rules |
| [`contracts/firestore.indexes.json`](../contracts/firestore.indexes.json) | Composite indexes |
| [`contracts/policy/reconciliation.v1.yaml`](../contracts/policy/reconciliation.v1.yaml) | Matching windows, tolerances, weights, thresholds |
| [`contracts/policy/risk.v1.yaml`](../contracts/policy/risk.v1.yaml) | Risk levels, rules, next-step catalog |
| [`contracts/policy/categorization-rules.v1.yaml`](../contracts/policy/categorization-rules.v1.yaml) | Keyword categorization rules |
| [`contracts/policy/forensics.v1.yaml`](../contracts/policy/forensics.v1.yaml) | Enabled checks, duplicate keys and thresholds |
| [`contracts/plans.v1.yaml`](../contracts/plans.v1.yaml) | Plans (free trial, coming-soon tiers), limits, coming-soon features, UI languages |
| [`contracts/design/tokens.json`](../contracts/design/tokens.json) | Design tokens (colour, type, space, radius, motion, breakpoints) |
| `contracts/data/schema-snapshot.json` | Persisted shapes for the schema drift gate (generated by spec 001) |
