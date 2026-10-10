# 10 — API Contract

> The authoritative, machine-readable contract is [`contracts/openapi.yaml`](../contracts/openapi.yaml)
> (OpenAPI 3.1). This page explains conventions and lists endpoints. When they disagree, the YAML wins
> and this page gets fixed.

---

## 1. Conventions

| Topic | Rule |
|---|---|
| Base path | `/api` on `kredibel-web`. Worker endpoints live under `/tasks` on `kredibel-worker` only. |
| Auth | `Authorization: Bearer <Firebase ID token>` on every `/api` route except `GET /api/health`. |
| Workspace scoping | `orgId` (the workspace) comes **only** from the verified token's custom claim, never from the path or body. A case or applicant from another workspace returns `404` (not `403`) so IDs can't be probed. Without a workspace, only `GET /api/me`, `GET /api/plans`, `POST /api/workspaces` and `POST /api/invites/{id}/accept` work; everything else returns `403 WORKSPACE_REQUIRED`. |
| Plan entitlements | Checked server-side where money or seats are spent: create case, upload, start run, invite ([`specs/013`](specs/013-workspace-and-plans/spec.md)). |
| Language | Responses are English. Errors carry a stable `code` so a future UI language can localize them. |
| Content type | `application/json; charset=utf-8`, except uploads (`multipart/form-data`) and file/page downloads. |
| Naming | `camelCase` JSON. |
| Money | `{"amount": "1250000.00", "currency": "IDR"}` |
| Dates | Calendar dates `YYYY-MM-DD`; instants RFC 3339 UTC (`2026-10-12T03:15:00Z`). |
| Pagination | Cursor-based: `?limit=` (default 50, max 200) and `?cursor=`; responses `{items, nextCursor}`. |
| Idempotency | `POST /analysis-runs` is safe to repeat: while a run is `QUEUED`/`RUNNING` it returns `409 ANALYSIS_ALREADY_RUNNING` with the existing `runId`. |
| Versioning | Additive changes only during the competition; breaking changes need an ADR. |
| Types for the SPA | Generated with `openapi-typescript` into `frontend/src/shared/api/schema.d.ts` (`npm run gen:api`). |

---

## 2. Endpoints

### 2.1 System

| Method & path | Purpose | P |
|---|---|---|
| `GET /api/health` | Liveness + version (no auth) | P0 |
| `GET /api/me` | Current user: uid, email, name, `orgId` (null before onboarding), role, `needsWorkspace`, workspace plan summary, language | P0 |

### 2.1a Workspace & plans ([spec 013](specs/013-workspace-and-plans/spec.md))

| Method & path | Purpose | P |
|---|---|---|
| `GET /api/plans` | Plan catalog (Free trial `AVAILABLE`; Starter, Professional, Enterprise `COMING_SOON`) and UI languages (English `available`, others `coming_soon`) | P0 |
| `POST /api/workspaces` | Create a workspace for a user who has none; starts the free trial; caller becomes `admin`; sets custom claims (client refreshes its token) | P0 |
| `GET /api/workspace` | Workspace profile, subscription state (trial days left, effective limits) and usage this month | P0 |
| `PATCH /api/workspace` | Name, time zone, language (`en` only) — admin; policy overrides (P1) — admin or risk lead | P0 / P1 |
| `GET /api/workspace/members` | Members and pending invites | P1 |
| `POST /api/workspace/invites` | Invite by email with a role (counts against seats; nothing is emailed) | P1 |
| `DELETE /api/workspace/members/{uid}` | Remove a member (not the last admin) | P1 |
| `POST /api/invites/{inviteId}/accept` | Join a workspace; the caller's verified email must match | P1 |

### 2.1b Applicants ([spec 003](specs/003-case-intake/spec.md), [spec 014](specs/014-applicant-profile-intelligence/spec.md))

| Method & path | Purpose | P |
|---|---|---|
| `POST /api/applicants` | Onboard an applicant: `INDIVIDUAL` or `COMPANY`, optional address, contact, bank accounts, related parties | P0 |
| `GET /api/applicants?q=&type=&limit=&cursor=` | List or search (name prefix) | P0 |
| `GET /api/applicants/{applicantId}` | Profile with bank accounts (masked), related parties, pending suggestion count | P0 |
| `PATCH /api/applicants/{applicantId}` | Edit profile fields (type is fixed) | P0 |
| `POST /api/applicants/{applicantId}/bank-accounts` · `DELETE …/{accountId}` | Add or remove a bank account (full number in, mask + hash stored) | P0 |
| `POST /api/applicants/{applicantId}/related-parties` · `DELETE …/{partyId}` | Add or remove a beneficial owner, director, shareholder, guarantor or signatory | P0 |
| `GET /api/applicants/{applicantId}/suggestions?status=` | AI-detected profile suggestions with evidence | P0 |
| `PATCH /api/applicants/{applicantId}/suggestions/{suggestionId}` | Accept (writes into the profile) or reject | P0 |
| `GET /api/applicants/{applicantId}/events` | Applicant audit trail | P0 |

### 2.2 Cases

| Method & path | Purpose | P |
|---|---|---|
| `POST /api/cases` | Create a case (`DRAFT`) for an existing `applicantId` or an inline new applicant | P0 |
| `GET /api/cases?status=&applicantId=&limit=&cursor=` | List cases, newest first | P0 |
| `GET /api/cases/{caseId}` | Case detail incl. applicant snapshot, summary and decision | P0 |
| `PATCH /api/cases/{caseId}` | Edit the loan request while `DRAFT` or `INFO_REQUESTED` (applicant details via `/api/applicants`) | P0 |

### 2.3 Documents

| Method & path | Purpose | P |
|---|---|---|
| `POST /api/cases/{caseId}/documents?split=none\|auto` | Upload one file (multipart field `file`); the server splits it into pages and triages each page. Returns `{items: [Document]}`. `split=auto` cuts an over-long PDF into parts (P1) | P0 / P1 |
| `GET /api/cases/{caseId}/documents` | List documents | P0 |
| `GET /api/cases/{caseId}/documents/{docId}` | Document detail (classification, extraction, integrity) | P0 |
| `DELETE /api/cases/{caseId}/documents/{docId}` | Remove while `DRAFT`/`INFO_REQUESTED` | P0 |
| `GET /api/cases/{caseId}/documents/{docId}/file` | Original file stream | P0 |
| `GET /api/cases/{caseId}/documents/{docId}/pages/{pageNo}?variant=full\|thumb` | Rendered page PNG | P0 |
| `PATCH /api/cases/{caseId}/documents/{docId}` | Override `docType` (re-run required) | P1 |

### 2.4 Analysis & results

| Method & path | Purpose | P |
|---|---|---|
| `POST /api/cases/{caseId}/analysis-runs` | Start a run → `202 {runId}` | P0 |
| `GET /api/cases/{caseId}/analysis-runs/{runId}` | Run status and stages | P0 |
| `GET /api/cases/{caseId}/analysis` | Current run's metrics, monthly flows, facts, scorecard, recommendation, reconciliation | P0 |
| `GET /api/cases/{caseId}/findings?severity=&category=&docId=&status=` | Current run's findings, most severe first | P0 |
| `PATCH /api/cases/{caseId}/findings/{findingId}` | Acknowledge or dismiss (reason required for dismiss) | P0 |
| `GET /api/cases/{caseId}/transactions?docId=&month=&category=&riskTag=&q=&limit=&cursor=` | Transactions | P0 |
| `PATCH /api/cases/{caseId}/transactions/{txId}` | Analyst re-categorization | P1 |
| `GET /api/cases/{caseId}/invoices?kind=` | Invoices with match status | P0 |
| `GET /api/cases/{caseId}/counterparties?role=` | Clients, suppliers, lenders, own accounts, related parties and other payees of the current run | P0 |
| `GET /api/cases/{caseId}/memo` | Memo with sections and grounding status | P0 |
| `PUT /api/cases/{caseId}/memo` | Save analyst edits; re-runs the grounding guard | P1 |

### 2.5 Decision & audit

| Method & path | Purpose | P |
|---|---|---|
| `POST /api/cases/{caseId}/decision` | Record `APPROVE`, `DECLINE`, `REQUEST_INFO` or `ESCALATE` | P0 |
| `GET /api/cases/{caseId}/events?limit=&cursor=` | Audit events, newest first | P0 |
| `POST /api/cases/{caseId}/info-request/draft` | Draft a borrower information request from findings (copy only, nothing sent) | P1 |

### 2.6 Assistant (P1)

| Method & path | Purpose |
|---|---|
| `GET /api/cases/{caseId}/assistant/messages` | Conversation history for the current user |
| `POST /api/cases/{caseId}/assistant/messages` | Ask a question → `{reply, citations}` (non-streaming) |

### 2.7 Policy (P1)

| Method & path | Purpose |
|---|---|
| `GET /api/policy` | The active scorecard policy with the workspace's overrides applied, read-only, for the "how is this scored?" panel |

### 2.8 Worker (internal)

| Method & path | Caller | Body |
|---|---|---|
| `POST /tasks/analyze-case` | Cloud Tasks with an OIDC token for `kredibel-tasks-invoker` | `{orgId, caseId, runId}` |

Returns `200` on success or when the run is already finished (idempotent); `5xx` to request a retry.
Returns `200` with `{"skipped": "stale"}` if `case.currentRunId != runId`.

---

## 3. Errors

All errors use **RFC 9457** `application/problem+json`:

```json
{
  "type": "/problems/open-critical-findings",
  "title": "Approval blocked by open critical findings",
  "status": 409,
  "detail": "2 critical findings are still open. Acknowledge or dismiss them first.",
  "code": "OPEN_CRITICAL_FINDINGS",
  "instance": "/api/cases/case_01J…/decision",
  "findingIds": ["fnd_7c1e…", "fnd_a90b…"]
}
```

| `code` | HTTP | When |
|---|---|---|
| `UNAUTHENTICATED` | 401 | Missing, invalid or expired token |
| `WORKSPACE_REQUIRED` | 403 | Signed in but no workspace yet (onboarding not done) |
| `ROLE_REQUIRED` | 403 | Action needs `risk_lead` or `admin` |
| `SIGNUP_CLOSED` | 403 | `SIGNUP_MODE` is `closed`, or `invite_only` without an invite, or `MAX_WORKSPACES` reached |
| `ALREADY_IN_WORKSPACE` | 409 | Creating a workspace or accepting an invite while already in one |
| `TRIAL_EXPIRED` | 403 | New case, upload or run after the free trial ended (`trialEndsAt` included); reads and decisions still work |
| `PLAN_LIMIT_REACHED` | 403 | A plan limit would be exceeded (`limit`, `used`, `max` included, e.g. `extractedPagesPerMonth`) |
| `LANGUAGE_NOT_AVAILABLE` | 422 | A language marked `coming_soon` was requested |
| `SUGGESTION_ALREADY_DECIDED` | 409 | Accepting or rejecting a suggestion that is no longer `PENDING`/`CONFLICT` |
| `LAST_ADMIN` | 409 | Removing or demoting the last admin (P1) |
| `NOT_FOUND` | 404 | Case/document/finding not found **or not in the caller's org** |
| `VALIDATION_ERROR` | 422 | Body/query invalid (`errors[]` lists fields) |
| `CASE_NOT_EDITABLE` | 409 | Edit or upload outside `DRAFT`/`INFO_REQUESTED` |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | Not PDF/PNG/JPEG by magic bytes |
| `DOCUMENT_TOO_LARGE` | 413 | Larger than the plan's `fileSizeMb` (20 MB on the free trial) |
| `TOO_MANY_PAGES` | 422 | More pages than the plan's `pagesPerDocument` (20); `maxPages` and `splitAvailable` included |
| `TOO_MANY_DOCUMENTS` | 409 | More than the plan's `documentsPerCase` (20) |
| `DUPLICATE_DOCUMENT` | 409 | Same SHA-256 already in the case (`existingDocId` included) |
| `ENCRYPTED_DOCUMENT` | 422 | Password-protected PDF |
| `NO_DOCUMENTS` | 409 | Starting analysis with no documents |
| `ANALYSIS_ALREADY_RUNNING` | 409 | A run is queued or running (`runId` included) |
| `RUN_QUOTA_EXCEEDED` | 429 | Org's daily run quota or the per-user rate limit reached (`retryAfterSeconds` included) |
| `RUNS_DISABLED` | 503 | New runs switched off by the `RUNS_ENABLED` kill switch; existing results stay readable |
| `ANALYSIS_NOT_READY` | 409 | Results requested before any successful run |
| `INVALID_TRANSITION` | 409 | Decision not valid from the current status |
| `OPEN_CRITICAL_FINDINGS` | 409 | Approve while a critical finding is open |
| `REASON_REQUIRED` | 422 | Dismiss/decline/override without a reason |
| `INTERNAL` | 500 | Unexpected; `detail` is generic, the log has the cause |

---

## 4. Representative payloads

### Create a case

```http
POST /api/cases
```

```json
{
  "applicant": {
    "type": "COMPANY",
    "company": {"legalName": "Sunrise Coffee Roasters", "legalForm": "PARTNERSHIP",
                "industry": "Coffee roasting & wholesale", "yearsOperating": 4},
    "bankAccounts": [{"bankName": "Archipelago Commerce Bank", "accountNumber": "9900004821",
                      "holderName": "SUNRISE COFFEE ROASTERS", "purpose": "OPERATING"}],
    "relatedParties": [{"name": "Andi Pratama", "kind": "INDIVIDUAL",
                        "roles": ["BENEFICIAL_OWNER", "DIRECTOR"], "ownershipPct": "60"}]
  },
  "request": {"amount": {"amount": "250000000.00", "currency": "IDR"}, "tenorMonths": 12,
              "purpose": "Working capital for green bean inventory"}
}
```

Or, for a returning applicant: `{"applicantId": "apl_01JA…", "request": {…}}`.

### Plan limit reached

```json
{
  "type": "/problems/plan-limit-reached",
  "title": "Plan limit reached",
  "status": 403,
  "detail": "This run needs 28 new pages but only 12 of your 300 monthly pages are left.",
  "code": "PLAN_LIMIT_REACHED",
  "limit": "extractedPagesPerMonth",
  "used": 288,
  "max": 300
}
```

### Profile suggestion (abridged)

```json
{
  "suggestionId": "sug_4b1d0e9a7c2f3a11",
  "field": "TAX_ID",
  "value": {"taxId": "99-731.204.5-018.000"},
  "display": "Tax ID 99-731.204.5-018.000",
  "confidence": "HIGH",
  "basis": "Printed as the issuer's tax ID on 10 sales invoices; agreed by both readings",
  "evidence": [{"docId": "doc_01JB…", "page": 1, "bbox": {"x0": 0.08, "y0": 0.16, "x1": 0.34, "y1": 0.18},
                "label": "Issuer tax ID"}],
  "status": "PENDING"
}
```

### Finding (abridged)

```json
{
  "findingId": "fnd_7c1e09a2b3d4e5f6",
  "runId": "run_01JA…",
  "code": "A01_RUNNING_BALANCE_BREAK",
  "category": "ARITHMETIC",
  "severity": "CRITICAL",
  "title": "Running balance does not add up",
  "facts": {"previousBalance": "41250000.00", "credit": "7250000.00", "debit": "0.00",
            "expectedBalance": "48500000.00", "printedBalance": "42500000.00"},
  "explanation": "On 14 March the statement adds a credit of IDR 7,250,000 but the printed balance rises by only IDR 1,250,000. Both readers agree on these values.",
  "evidence": [{"docId": "doc_01JA…", "page": 2, "bbox": {"x0": 0.71, "y0": 0.42, "x1": 0.93, "y1": 0.45},
                "txId": "tx_3f2a…", "label": "Credit amount"}],
  "detectedBy": "RULE",
  "status": "OPEN"
}
```

### Decision

```json
{"outcome": "DECLINE", "reason": "March statement altered; revenue not supported by bank inflows."}
```
