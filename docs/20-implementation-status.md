# 20 — Implementation Status

> What is actually built. Updated in the **same commit** as any change that adds, completes or removes
> a component. Statuses: **Specified** → **In progress** → **Built** (tests green) → **Deployed**
> (running on Cloud Run) · **Cut** (deliberately dropped, with reason).

_Last updated: 11 Oct 2026 — Spec 001 Foundation complete (tests green) and deployed to Cloud Run (cloud-hack2skill, asia-southeast1)._

## Foundation & platform

| Component | Spec | Status | Notes |
|---|---|---|---|
| Repo layout, Makefile, quality gates | 001 | Built | `make check` all 7 gates green (AC-001-11, AC-001-12) |
| Settings, logging, errors, auth, security headers | 001 | Deployed | Tests green (AC-001-1, AC-001-4, AC-001-5, AC-001-6, AC-001-10); running on Cloud Run |
| Design foundation: tokens, app shell, Storybook, visual tests, raw-style gate | 001 | Built | Tokens compile, AppShell responsive (360–1600px), Storybook 10, Playwright visual tests at 390/834/1440, no_raw_styles check (AC-001-15, AC-001-16, AC-001-17, AC-001-18) |
| Data-migration foundation: versions, upcasters, runner, job, backups | 001 | Deployed | Upcasters, runner with emulator, schema drift check, `kredibel-migrate` Cloud Run job, backup bucket and PITR (AC-001-19, AC-001-20, AC-001-21, AC-001-22) |
| Dockerfile, Cloud Build, bootstrap, Firebase | 001 | Deployed | Multi-stage Dockerfile, Cloud Build pipeline, web & worker deployed, Firebase Auth configured with demo user (AC-001-8, AC-001-9) |
| Cost guardrails: budget, AR cleanup, run quotas, kill switch | 001, 004 | Deployed | GCP budget 50/90/100% alerts, Artifact Registry 3-version cleanup policy, run quotas in env (docs/21 §7) |
| i18n scaffold (English only) | 001 | Built | `i18next` + `react-i18next` with `en` bundle (AC-001-14) |
| Synthetic books S1–S5, scan variant, fixtures | 002 | Specified | |
| Synthetic S6 (hidden instructions) | 002 | Specified (P1) | |

## Workspace & plans

| Component | Spec | Status | Notes |
|---|---|---|---|
| Plans config + entitlement checks | 013 | Specified | `contracts/plans.v1.yaml`, ADR-011 |
| Onboarding as individual or company (free trial, claims, first bank account) | 013 | Specified | `SIGNUP_MODE`, `MAX_WORKSPACES` |
| Usage counters + page reservation at upload | 013, 003 | Specified | |
| Settings: profile, bank accounts, language, plan & usage (coming soon items) | 013 | Specified | |
| Members and roles (owner, accountant, reviewer, viewer) | 013 | Specified (P1) | |

## Intake & workflows

| Component | Spec | Status | Notes |
|---|---|---|---|
| Upload API + sheet (camera on phones), page split + triage | 003 | Specified | |
| Exact duplicates (`D01`) | 003 | Specified | |
| Documents library + document page | 003 | Specified | |
| Queues, runs, worker endpoints, inline mode | 004 | Specified | |
| `document_workflow` and `month_workflow` skeletons; generations and debounce | 004 | Specified | Depends on spike S2 |
| Live progress (documents and months) | 004 | Specified | |

## Reading, checks and reconciliation

| Component | Spec | Status | Notes |
|---|---|---|---|
| Classifier (Flash-Lite) + `CONFIRM_TYPE` | 005 | Specified | |
| Gemini page and receipt readers (image only) | 005 | Specified | Depends on spike S1 |
| Witness: text layer + Document AI OCR | 005 | Specified | ADR-010; spike S3 |
| Normalization + verifier + provenance | 005 | Specified | |
| Ledger import (mapper proposes, user confirms, code parses) | 005 | Specified | |
| Escalation to Form/Invoice Parser, thorough mode | 005 | Specified (P1) | |
| Content duplicates `D02`–`D06` (held) | 006 | Specified | |
| Integrity checks `A01`, `A02`, `A04`, `M01`–`M04`, `M06`, `E0x`, `X05`, `X06` + verdict | 006 | Specified | |
| Categorization | 007 | Specified | |
| `reconcile_month` (order-independent) + figures | 007 | Specified | |
| Month checks `X01`, `X02`, `X08`, `X09`, `R01`, `R02`, `B01`, `B04`, `C02`, `D07` | 007 | Specified | |
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
| Traces in Cloud Trace + ADK dev UI (`make dev-agents`) | 001, 004, 017 | Specified | ADR-017 |

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

_None yet. Record every deliberate deviation here with the reason and the doc that was updated._
