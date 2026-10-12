# 20 — Implementation Status

> What is actually built. Updated in the **same commit** as any change that adds, completes or removes
> a component. Statuses: **Specified** → **In progress** → **Built** (tests green) → **Deployed**
> (running on Cloud Run) · **Cut** (deliberately dropped, with reason).

_Last updated: 12 Oct 2026 — Spec 007 candidate scoring and honest skeleton month state built; bank evidence/support and fixed-workspace-currency agreement specified in ADR-025 and mocked. Assignment, persistence, currency-confirmation UI and live reconciliation remain open. Specs 001, 003, 004 and 013 (P0) built; remaining reading work is listed below._

## Foundation & platform

| Component | Spec | Status | Notes |
|---|---|---|---|
| Repo layout, Makefile, quality gates | 001 | Built | `make check` all 8 gates green, the synthetic generator's own checks included (AC-001-11, AC-001-12) |
| Settings, logging, errors, auth, security headers | 001 | Deployed | Tests green (AC-001-1, AC-001-4, AC-001-5, AC-001-6, AC-001-10); running on Cloud Run |
| Design foundation: tokens, app shell, Storybook, visual tests, raw-style gate | 001 | Built | Tokens compile, AppShell responsive (360–1600px), Storybook 10, Playwright visual tests at 390/834/1440, no_raw_styles check (AC-001-15, AC-001-16, AC-001-17, AC-001-18) |
| Data-migration foundation: versions, upcasters, runner, job, backups | 001 | Deployed | Upcasters, runner with emulator, schema drift check, `kredibel-migrate` Cloud Run job, backup bucket and PITR (AC-001-19, AC-001-20, AC-001-21, AC-001-22) |
| Dockerfile, Cloud Build, bootstrap, Firebase (Auth + Hosting) | 001 | Deployed | Multi-stage Dockerfile, Cloud Build pipeline, web & worker deployed, Firebase Auth & Hosting (kredibel-app.web.app) deployed with demo user (AC-001-8, AC-001-9) |
| Cost guardrails: budget, AR cleanup, run quotas, kill switch | 001, 004 | Deployed | GCP budget 50/90/100% alerts, Artifact Registry 3-version cleanup policy, run quotas in env (docs/21 §7) |
| i18n scaffold (English only) | 001 | Built | `i18next` + `react-i18next` with `en` bundle (AC-001-14) |
| Synthetic books S1–S5, scan variant, fixtures | 002 | Built | `tools/synthetic` (`make synth`): books as data, AUTO/PROPOSED proven against the reconciliation policy, deterministic PDFs/JPEGs/CSV/XLSX, T1 and T7–T13, `truth.json`, `--scan`, 8 fixtures; 213 generator tests in `make check`. Demo set generated, not committed |
| Synthetic S6 (hidden instructions) | 002 | Specified (P1) | |

## Workspace & plans

| Component | Spec | Status | Notes |
|---|---|---|---|
| Plans config + entitlement checks | 013 | Built | Catalog validated at start-up; pure checks; `EntitlementService` meters in the same Firestore transaction (T013-01…03, T013-07); wired into upload and user month runs, every `403`/`413`/`422`/`429` code tested through the API (T013-10). The assistant's daily question limit arrives with spec 011 (T011-04) |
| Onboarding as individual or company (free trial, claims, currency, first bank account) | 013 | Built | One-transaction create with double-submit and claims-repair guard; routes; onboarding page with token refresh and retry; demo seed (T013-04…06, -08, -09, -11). Verify on Cloud Run: T013-18; currency chosen at onboarding (IDR, MYR, SGD, JPY, USD), fixed afterwards, support script (ADR-020) |
| Usage counters + page reservation at upload | 013, 003 | Built | Counters, reservation and settlement integrated into upload with Firestore transactions (AC-003-3, AC-003-4) |
| Settings: profile, bank accounts, language, plan & usage (coming soon items) | 013 | Built | API and UI built; ProfileForm, BankAccountsSection, LanguageSettings, PlanAndUsage, and PlanLimitDialog fully tested with unit and integration tests (T013-08, T013-12…15) |
| Members and roles (owner, accountant, reviewer, viewer) | 013 | Specified (P1) | |

## Intake & workflows

| Component | Spec | Status | Notes |
|---|---|---|---|
| Upload API + sheet (camera on phones), page split + triage | 003 | Built | Sniffing, triage, rendering, storage, Cloud Tasks enqueue, UploadSheet with mobile camera (AC-003-1…4) |
| Exact duplicates (`D01`) | 003 | Built | SHA-256 duplicate detection, DUPLICATE record, no re-read, upload UI duplicate notice (AC-003-5, AC-003-6) |
| Documents library + document page | 003 | Built | Documents list with filters & live badges, Document detail with page viewer, extracted values, and delete cascade (AC-003-7…11) |
| Queues, runs, worker endpoints, inline mode | 004 | Built | Generation bump and task name in one transaction, debounce, Cloud Tasks and inline queue, OIDC-only `/tasks/*` on the worker, idempotent re-delivery (T004-02…04) |
| `document_workflow` and `month_workflow` skeletons; generations and debounce | 004 | Built | Spike S2 done; both workflows run with stub nodes, `SUPERSEDED` and `NEEDS_INPUT` paths, burst of 10 changes → one effective run (T004-05…08). Real nodes arrive with specs 005–008 |
| Live progress (documents and months) | 004 | Built | Firestore listeners, `ProgressLine`, runs API; `RUNS_ENABLED` kill switch and daily quotas with "paused until tomorrow" (T004-09, T004-10) |

## Reading, checks and reconciliation

| Component | Spec | Status | Notes |
|---|---|---|---|
| Classifier (Flash-Lite) + `CONFIRM_TYPE` | 005 | In progress | `classify_document` on `MODEL_LITE` from page 1's image and chunks; below 0.6 → `NEEDS_INPUT` with `E03_UNCERTAIN_TYPE`. The `CONFIRM_TYPE` review item comes with spec 009 |
| Gemini page readers: statements, invoices, receipts | 005 | Built | Image plus numbered layout chunks with citations (ADR-023), `thinking_level=low`, timeout and one retry, cached per page image + model + prompt. Real RHB statement: 13 pages, 178 lines, 718/718 values grounded; real MY/ID invoices and receipts 90–100 % |
| Witness: text layer + Document AI OCR | 005 | In progress | Text layer → layout chunks built (`parse_pages`); Enterprise OCR for scans and photos waits for spike S3, so a scan's values are `SINGLE_SOURCE` |
| Normalization + verifier + provenance | 005 | Built | `normalize.py` (EN/EU and dot-grouped amounts, `Rp.`/`RM`, English, Malay and Indonesian months), `layout.py` chunks, `verify.py` grounding, records with per-value `consensus` (status, page, box, raw readings); the document page lights each value on its page |
| Ledger import (mapper proposes, user confirms, code parses) | 005 | Specified | |
| Escalation to Form/Invoice Parser, thorough mode | 005 | Specified (P1) | |
| Content duplicates `D02`–`D06` (held) | 006 | In progress | `D02`–`D05` built: the newer document and its records are held, a `DUPLICATE` finding names the earlier one, and deleting the earlier copy re-reads and releases it; library and document page show "Possible copy". D05 image similarity no longer overrides contradictory merchant/date/total readings (T006-01a): different till rolls remain eligible. The `POSSIBLE_DUPLICATE` item and decisions (009) and `D06` (ledger import) remain open |
| Integrity checks `A01`, `A02`, `A04`, `M01`–`M04`, `M06`, `E01`, `E02`, `E05`, `X05`, `X06`; verdict; findings API and document page | 006 | Built | `inspect_file` (pikepdf metadata, saves excluding linearization, what each later save changed, fonts of values) and `check_document` (policy-enabled checks, upsert by ID with the re-run rules, verdict). S2's edited March statement → `TAMPERED` with all six expected codes; S1 → `CLEAN`. `M04` is measured per page, not per column (docs/08 §2.4) |
| Integrity checks `A01`, `A02`, `A04`, `M01`–`M04`, `M06`, `E0x`, `X05`, `X06` + verdict | 006 | Specified | |
| Categorization | 007 | In progress | `categorize_bank_lines`: keyword rules first (`categorization-rules.v1.yaml`), then `MODEL_LITE` in cached batches of 100 with only the categories allowed for the line's direction; confidence < 0.5 → `UNKNOWN`; cash-flow class from the workspace's framework; risk tags; the model also cleans counterparty names. Match-decided and user categories come with matching and the month page |
| Candidate scoring and eligibility | 007 | Built | T007-03: Decimal amount/date/party/reference contributions, currency floors selected by fixed workspace currency, explicit agreement for printed-currency mismatches without conversion, direction/account/receipt-method gates and review-only tax shortfalls; 59 synthetic unit tests. Pure scorer only; not wired into production matching |
| `reconcile_month` (order-independent) + figures | 007 | Built | Scoring, deterministic assignment (single, grouped, split; manual matches kept, rejections never return; Hypothesis order test), payment evidence and coverage, bank support, figures as facts, a person's decisions (`/api/decisions`), and the month run writing matches, evidence, support, figures and an honest state. Statement + invoice end to end: `AUTO` match with all reasons, `PAID_BANK`, month `RECONCILED`. Open: S1/S4/S5 scenario gates, cross-month order, ledger pairs |
| Bank evidence, supporting documents and manual attestations | 007 | Specified | ADR-025 / FR-036…038: bank-only rows are informational, document approval and payment confirmation are separate, no fabricated cash; fixed currency with audited agreement before interpreting differently printed amounts. Responsive prototype `reconciliation.html`; persistence/API/migration and real UI remain T007-06a/T007-10 |
| Month checks `X01`, `X02`, `X08`, `X09`, `R01`, `R02`, `B01`, `B04`, `C02`, `D07` | 007 | Built | All but `X09` (needs ledger import); run by `check_month` with month-scoped findings |
| Months page, manual match and unmatch | 007 | Specified | |
| Counterparties (accounts seen) + profile suggestions | 014 | Specified | |
| Risk levels + next-step catalog | 008 | Specified | |
| Explainer + grounding guard | 008 | Specified | |

## Review, risk and insight

| Component | Spec | Status | Notes |
|---|---|---|---|
| Review queue (8 kinds, actions, auto-advance) | 009 | Specified | |
| Risk page + evidence viewer | 008 | Specified | |
| Dashboard (KPIs, month strip, alerts, review preview) | 010 | Specified | |
| Money flow (Flow, Bars, Table, By client and supplier) + drill-down | 010 | Specified | Statement view (IFRS or US GAAP) by default; full-width charts, one per row |
| Months in and out, cash-flow statement waterfall | 010 | Specified | `GET /api/cash-flow`; docs/08 §5.2 |
| Category → cash-flow class per framework | 007, 016 | Specified | `contracts/policy/categories.v1.yaml` |
| Traces in Cloud Trace + local OTel + ADK dev UI | 001, 004, 017 | Built | One trace per run, `runs.traceId`, node spans and direct Gemini SDK attempts with model, prompt version, tokens and sanitized errors. Cloud Run uses `TRACE_EXPORT=cloud`; `make trace-up` / `make dev-traced` export locally to Jaeger at :16686. `make trace-smoke` verified ingestion; retries/content-exclusion tests and `make check` pass. `make dev-agents` has fixture apps for both workflows. Guide in docs/23 |

## P1

| Component | Spec | Status | Notes |
|---|---|---|---|
| Model Armor screening + quarantine | 015 | Specified | Depends on spike S4 |
| Run graph | 015 | Specified | ADK traces, docs/17 §5 |
| Finance Assistant (tools, Firestore vector retrieval, Sessions, Memory Bank) | 011 | Specified | ADR-014; spike S5 |
| DeepEval suite for the assistant | 011, 012 | Specified | Gemini judge on Agent Platform |
| Month sign-off | 015 | Specified | |
| Revision diff, `M05`, `A03`, `A05` | 015 | Specified | |
| Visual forensics | 015 | Specified | |
| Reconciliation CSV export | 015 | Specified | |
| Split and upload | 015 | Specified | |
| Aliases and related parties | 014 | Specified | |
| Evals + README results | 012 | Specified | P0 suites always on D6 |
| Labels: writers, Labels page, decisions, verified examples, E-LBL | 016 | Specified | ADR-016; `learning.v1.yaml` |
| Page extraction Markdown | 016 | Specified | GCS `extractions/` |
| Run history in BigQuery (ADK plugin), Runs page, Looker Studio report | 017 | Specified | ADR-017 |
| Dataset export for tuning (consent, masking) | 016 | Later | Not in the hackathon |

## Deviations from the docs

_Record every deliberate deviation here with the reason and the doc that was updated._

| Date | Deviation | Reason | Docs updated |
|---|---|---|---|
| 11 Oct 2026 | Firebase Hosting serves the SPA and rewrites `/api/**` to `kredibel-web` (ADR-008 had Cloud Run only) | Stable demo URL and edge-served assets; same origin kept | [ADR-018](adr/ADR-018-firebase-hosting-in-front-of-cloud-run.md); `14` §8, `16` §5 and §8, `21`, `05` §3, ADR-008 status. **Open:** `diagrams/gcp-architecture.drawio.svg` still shows Cloud Run only; update it with the draw.io extension. |
| 11 Oct 2026 | CI `frontend-check` runs ESLint, tsc, Vitest, `tokens-check` and `no_raw_styles`; the Playwright visual tests and Storybook axe checks of docs/16 §8 run locally only; `backend-check` skips the Firestore emulator tests | Visual baselines are recorded on macOS (`-darwin.png`), the Storybook test runner was never installed (T001-29), and the Cloud Build step has no emulator | **Open:** record `-linux.png` baselines in the Playwright Docker image, add the Storybook Vitest a11y runner, and run `backend-check` in the `google-cloud-cli:emulators` image; then enforce all three. Locally `make docker-up` + `make check` runs everything. |
| 12 Oct 2026 | Spec 007 P0 distinguishes bank evidence from support and adds manual attestations and currency agreement (no FX); low auto-match rate alone no longer implies fraud risk | Product-owner clarification; statement-only rows are valid bank cash evidence | ADR-025, PRD, docs/06, 08, 09, 11, spec 007 and policies. Actual decision endpoints and risk/review integration are still open. |

### Spec 007 validation (12 Oct 2026)

`make check`: 473 backend, 95 frontend and 213 synthetic tests pass, including emulator integration.
The new ordinary-flow mock uses existing kit classes; no React screen is shipped by this task.
Checked its three states at 360/390/834/1440/1600 px: no horizontal page overflow, action targets
at least 44 px, correct fixed workspace currency in the shell. Added action-preview feedback and
used the existing large-button variant after the first visual check found 40 px desktop actions.
Screenshots are recorded at 390/834/1440. The Python screenshot runner expected an absent Chromium
revision; the installed frontend Playwright browser captured the same mock locally instead.
