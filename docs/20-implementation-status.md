# 20 — Implementation Status

> What is actually built. Updated in the **same commit** as any change that adds, completes or removes
> a component. Statuses: **Specified** → **In progress** → **Built** (tests green) → **Deployed**
> (running on Cloud Run) · **Cut** (deliberately dropped, with reason).

_Last updated: 10 Oct 2026 — documentation complete, no code yet._

## Foundation & platform

| Component | Spec | Status | Notes |
|---|---|---|---|
| Repo layout, Makefile, quality gates | 001 | Specified | |
| Settings, logging, errors, auth, security headers | 001 | Specified | |
| SPA shell, sign-in, API client | 001 | Specified | |
| Dockerfile, Cloud Build, bootstrap, Firebase | 001 | Specified | |
| Cost guardrails: budget, AR cleanup, run quotas, kill switch | 001, 004 | Specified | docs/21 |
| Per-page content-addressed extraction cache | 005 | Specified | docs/21 §5 |
| i18n scaffold (English only) | 001 | Specified | NFR-11 |
| Synthetic generator S1–S3 + applicants + scanned variant + fixtures | 002 | Specified | |
| Synthetic generator S4–S7 | 002 | Specified (P1) | |

## Workspace & plans

| Component | Spec | Status | Notes |
|---|---|---|---|
| Plans config + entitlement checks | 013 | Specified | `contracts/plans.v1.yaml`, ADR-011 |
| Workspace onboarding (self-serve, free trial, claims) | 013 | Specified | `SIGNUP_MODE`, `MAX_WORKSPACES` |
| Usage counters + page reservation | 013, 004 | Specified | |
| Settings: workspace, language (English only), plan & usage | 013 | Specified | Coming-soon tiers and languages |
| Members & invites | 013 | Specified (P1) | |
| Credit-policy overrides | 013 | Specified (P1) | |

## Intake & orchestration

| Component | Spec | Status | Notes |
|---|---|---|---|
| Applicant onboarding (individual / company, accounts, related parties) | 003 | Specified | ADR-012 |
| Cases API + wizard UI | 003 | Specified | |
| Documents upload/view API + UI, page split + triage | 003 | Specified | |
| Split and upload for long PDFs | 003 | Specified (P1) | |
| Runs API, Cloud Tasks, worker, inline mode | 004 | Specified | |
| ADK `case_pipeline` skeleton + progress | 004 | Specified | Depends on spike S2 |
| Live progress UI | 004 | Specified | |

## Document intelligence & risk engine

| Component | Spec | Status | Notes |
|---|---|---|---|
| PDF inspector | 005 | Specified | |
| Classifier (Flash-Lite, page 1) | 005 | Specified | |
| Gemini page reader (image only) | 005 | Specified | Depends on spike S1 |
| Witness: text layer + Document AI OCR | 005 | Specified | ADR-010 |
| Normalization + verifier + provenance | 005 | Specified | |
| Escalation to Form/Invoice Parser, thorough mode | 005 | Specified (P1) | |
| Forensics P0 (A01, A02, A04, M01–M04, M06, X01, X05, E01–E05) | 006 | Specified | |
| Integrity verdict + explanations | 006 | Specified | |
| Categorization | 007 | Specified | |
| Cash-flow metrics + facts | 007 | Specified | |
| Reconciliation | 007 | Specified | |
| Case-wide findings P0 (R01, R02, C01, C02, B01, B04) | 007 | Specified | |
| Counterparty directory | 014 | Specified | |
| Profile suggestions + `X06` | 014 | Specified | |
| Scorecard + hard stops | 008 | Specified | |
| Memo writer + grounding guard | 008 | Specified | |

## Review

| Component | Spec | Status | Notes |
|---|---|---|---|
| Case state machine + decision API | 009 | Specified | |
| Workspace tabs | 009 | Specified | |
| Evidence viewer | 009 | Specified | |
| Decision panel | 009 | Specified | |
| Applicant tab (profile, suggestions, counterparties) | 014 | Specified | |

## P1

| Component | Spec | Status | Notes |
|---|---|---|---|
| Model Armor screening + quarantine | 010 | Specified | Depends on spike S4 |
| Revision recovery | 010 | Specified | |
| Run timeline | 010 | Specified | |
| Visual forensics | 010 | Specified | Depends on spike S5 |
| Remaining checks | 010 | Specified | |
| Case assistant | 011 | Specified | |
| Evals + README results | 012 | Specified | |
| Memo edit, re-categorize, info-request letter | 009 (P1) | Specified | |
| Related parties, key counterparties, `B07`, `X07` | 014 (P1) | Specified | |
| Pre-fill on upload, applicant list page | 014 (P1) | Specified | |

## Deviations from the docs

_None yet. Record every deliberate deviation here with the reason and the doc that was updated._
