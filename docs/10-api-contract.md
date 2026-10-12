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
| Workspace scoping | `orgId` comes **only** from the verified token's custom claim, never from the path or body. A record of another workspace returns `404` (not `403`) so IDs cannot be probed. Without a workspace, only `GET /api/me`, `GET /api/plans`, `POST /api/workspaces` and `POST /api/invites/{inviteId}/accept` work; everything else returns `403 WORKSPACE_REQUIRED`. |
| Roles | P0: the creator is `owner` and may do everything. P1 adds `accountant`, `reviewer`, `viewer` (§5). Checked in the service layer, not only hidden in the UI. |
| Plan entitlements | Checked server-side where money or seats are spent: upload, month run, assistant question, invite ([spec 013](specs/013-workspace-and-plans/spec.md)). |
| Realtime | The SPA listens to Firestore for `documents/{docId}` (status, pages), `months/{yyyy-mm}` (state, figures, risk) and `runs/{runId}`; the API is used for everything else. |
| Language | Responses are English. Errors carry a stable `code` so a future UI language can localize them. |
| Content type | `application/json; charset=utf-8`, except uploads (`multipart/form-data`) and file or page downloads. |
| Naming | `camelCase` JSON. |
| Money | `{"amount": "1250000.00", "currency": "IDR"}`, signed for bank lines (+ in, − out). |
| Dates and months | Calendar dates `YYYY-MM-DD`; months `YYYY-MM`; instants RFC 3339 UTC. |
| Periods | `period=` is a month (`2026-03`), a quarter (`2026-Q1`), a year (`2026`), a range (`2026-01..2026-06`) or `all`. |
| Pagination | Cursor-based: `?limit=` (default 50, max 200) and `?cursor=`; responses `{items, nextCursor}`. |
| Idempotency | Uploads are keyed by SHA-256 (an exact copy returns the existing record as a duplicate, never an error). Resolving a review item that is already resolved returns `409 ITEM_ALREADY_RESOLVED`. Worker tasks are idempotent by `runId`. |
| Versioning | Additive changes only during the competition; breaking changes need an ADR. Response bodies never expose `schemaVersion`. |
| Types for the SPA | Generated with `openapi-typescript` into `frontend/src/shared/api/schema.d.ts` (`npm run gen:api`). |

---

## 2. Endpoints

### 2.1 System, workspace and plans

| Method & path | Purpose | P |
|---|---|---|
| `GET /api/health` | Liveness + version (no auth) | P0 |
| `GET /api/me` | Current user: uid, email, name, `orgId` (null before onboarding), role, `needsWorkspace`, plan summary | P0 |
| `GET /api/plans` | Plan catalog (Free trial `AVAILABLE`; others `COMING_SOON`), coming-soon features, UI languages | P0 |
| `POST /api/workspaces` | Create the workspace: name, `entityType` (`INDIVIDUAL` or `COMPANY`), profile basics, time zone, `currency` (`IDR`, `MYR`, `SGD`, `JPY`, `USD`; fixed afterwards); starts the free trial; caller becomes `owner` | P0 |
| `GET /api/workspace` | Profile, subscription (trial days left, effective limits), usage this month, counts | P0 |
| `PATCH /api/workspace` | Profile fields (incl. `accountingFramework`: `IFRS` or `US_GAAP`), time zone, language (`en` only), `learning.shareVerifiedLabels`; entity type is fixed | P0 / P1 |
| `GET /api/bank-accounts` · `POST /api/bank-accounts` · `PATCH /api/bank-accounts/{accountId}` · `DELETE /api/bank-accounts/{accountId}` | The workspace's bank accounts (full number in, mask + hash stored); `ledgerAccountCode` for ledger reconciliation | P0 |
| `GET /api/workspace/members` · `POST /api/workspace/invites` · `DELETE /api/workspace/members/{uid}` · `POST /api/invites/{inviteId}/accept` | Team members and roles (nothing is emailed; invite link only) | P1 |

### 2.2 Documents

| Method & path | Purpose | P |
|---|---|---|
| `POST /api/documents` | Upload one file (multipart field `file`; optional `docTypeHint`). Returns `201` with the document: `UPLOADED`, or `DUPLICATE` with `duplicate.kind = EXACT` and `ofDocId` when the same file exists (not read, not counted) | P0 |
| `GET /api/documents?type=&month=&status=&duplicate=&risk=&limit=&cursor=` | Library, newest first | P0 |
| `GET /api/documents/{docId}` | Detail: classification, reading, statement or ledger meta, integrity verdict, risk, duplicate state, pages | P0 |
| `DELETE /api/documents/{docId}` | Remove a document and everything read from it; marks its months dirty (blocked in a signed-off month, P1) | P0 |
| `GET /api/documents/{docId}/file` | Original file stream | P0 |
| `GET /api/documents/{docId}/pages/{pageNo}?variant=full\|thumb` | Rendered page PNG | P0 |
| `GET /api/documents/{docId}/pages/{pageNo}/extraction.md` | The page as read, in Markdown: page type and confidence, reading method, witness text, line items, both readings of each value ([ADR-016](adr/ADR-016-human-verified-labels-and-learning-loop.md)) | P1 |
| `GET /api/documents/{docId}/ledger-mapping` | The proposed or confirmed column mapping with the header and 5 sample rows parsed both ways | P0 |
| `POST /api/documents/{docId}/reprocess` | Read again (after a type change or a failure); counts against the page limit | P1 |

### 2.3 Books: bank lines, invoices, receipts, ledger

| Method & path | Purpose | P |
|---|---|---|
| `GET /api/bank-lines?docId=&month=&accountId=&matchState=&category=&counterpartyId=&q=&flow=` | Bank lines with each value's readings (status, page, box); `docId` gives one statement's lines (the document page); `flow` is a money-flow link ID (Sankey drill-down) | P0 |
| `PATCH /api/bank-lines/{txId}` | Change the category (`categorizedBy: USER`); same as correcting its `CATEGORY` label (§2.10); marks the month dirty | P0 |
| `GET /api/invoices?kind=&month=&paymentState=&counterpartyId=` · `GET /api/invoices/{invoiceId}` | Sales and purchase invoices with payment state and matches | P0 |
| `GET /api/receipts?month=&paymentState=` · `GET /api/receipts/{receiptId}` | Receipts | P0 |
| `GET /api/ledger-entries?month=&isBankCash=&matchState=&accountCode=` | Imported ledger entries | P0 |

### 2.4 Months and reconciliation

| Method & path | Purpose | P |
|---|---|---|
| `GET /api/months` | Every month with data: state, statement presence per account, risk level, auto-match rate, open items (the month strip) | P0 |
| `GET /api/months/{month}` | Figures (facts), risk (level, summary, next steps, reasons), statements, counts, last run | P0 |
| `POST /api/months/{month}/reconcile` | Re-run now (normally automatic after any change) → `202 {runId}` | P0 |
| `GET /api/matches?month=&status=&kind=` | Matches with members, method, score and reasons | P0 |
| `POST /api/matches` | Manual match: bank line IDs + invoice, receipt or ledger entry IDs (amounts must agree within tolerance); marks the month dirty | P0 |
| `DELETE /api/matches/{matchId}` | Unmatch: the match becomes `REJECTED` and is never proposed again | P0 |
| `POST /api/months/{month}/sign-off` · `POST /api/months/{month}/reopen` | Lock a reconciled month; reopen with a reason | P1 |
| `GET /api/exports/reconciliation.csv?month=` | Reconciliation and review log | P1 |

### 2.5 Review queue

| Method & path | Purpose | P |
|---|---|---|
| `GET /api/review-items?status=&kind=&month=&limit=&cursor=` | Open items, highest priority first | P0 |
| `GET /api/review-items/{itemId}` | Item with its subject records, the suggested fix and candidates | P0 |
| `POST /api/review-items/{itemId}/resolve` | Resolve with one action allowed for the item's kind (§4); writes an event and marks the month dirty | P0 |

Every exception in the product (proposed match, unmatched line, possible duplicate, uncertain value,
ledger difference, document type, ledger mapping) is closed through this one endpoint.

### 2.6 Risk and evidence

| Method & path | Purpose | P |
|---|---|---|
| `GET /api/findings?scope=&month=&docId=&severity=&status=&code=` | Findings, most severe first | P0 |
| `GET /api/findings/{findingId}` | Finding with facts, evidence, explanation and next steps | P0 |
| `PATCH /api/findings/{findingId}` | Acknowledge or dismiss (reason required to dismiss a `CRITICAL` or `HIGH` finding) | P0 |
| `GET /api/policy` | Read-only summary of the active checks, reconciliation thresholds and risk rules ("How is this decided?") | P1 |

### 2.7 Dashboard and insight

| Method & path | Purpose | P |
|---|---|---|
| `GET /api/dashboard?period=` | KPIs (money in, money out, net, auto-match rate, open review items, documents waiting), months with risk, top alerts, review preview | P0 |
| `GET /api/money-flow?period=&view=&framework=&accountId=&showTransfers=` | Sankey `{nodes, links}`. `view=STATEMENT` (default): sources → accounts → activity → statement line under the framework (default: the workspace's); `view=COUNTERPARTIES`: sources → accounts → who was paid ([`08`](08-risk-engine.md) §5.1). Each link has an ID usable as `flow=` on `/api/bank-lines` | P0 |
| `GET /api/cash-flow?period=&framework=` | Months in, out, net and closing balance; the cash-flow statement by activity and by line, with the opening-to-closing check ([`08`](08-risk-engine.md) §5.2) | P0 |
| `GET /api/counterparties?role=&q=` · `GET /api/counterparties/{counterpartyId}` | Clients and suppliers with totals per month and accounts seen | P0 |
| `GET /api/suggestions?status=` · `PATCH /api/suggestions/{suggestionId}` | Profile suggestions from documents; accept or reject | P0 |
| `GET /api/events?subject=&type=&limit=&cursor=` | Audit trail, newest first | P0 |
| `GET /api/runs?kind=&target=&status=&hasCorrections=` · `GET /api/runs/{runId}` | Workflow runs with stages, models, prompt versions, label counts and the Cloud Trace link; the run graph (P1) draws from `stages[]` | P0 / P1 |
| `GET /api/runs/{runId}/events` | The run's agent events from BigQuery (LLM and tool calls, node outputs, errors) with span IDs, tokens and latency, joined to the labels they produced; content only where captured ([ADR-017](adr/ADR-017-agent-observability-on-google-cloud.md)); owner only | P1 |

### 2.8 Finance Assistant (P1, [ADR-014](adr/ADR-014-finance-assistant-tools-rag-memory.md))

| Method & path | Purpose |
|---|---|
| `GET /api/assistant/threads` · `POST /api/assistant/threads` | The user's conversations; a thread may be scoped to a month |
| `GET /api/assistant/threads/{threadId}/messages` | Messages from the managed session |
| `POST /api/assistant/threads/{threadId}/messages` | Ask → `{answer: {parts[], citations[], grounding}}`; `Accept: text/event-stream` streams the same parts |
| `GET /api/assistant/memories` · `DELETE /api/assistant/memories` | What the assistant remembers about the user's preferences; forget all |

### 2.10 Labels and learning (P1, [ADR-016](adr/ADR-016-human-verified-labels-and-learning-loop.md))

| Method & path | Purpose | P |
|---|---|---|
| `GET /api/labels?task=&status=&needsCheck=&docId=&month=&datasetUse=&sort=&limit=&cursor=` | Labels, lowest confidence first, with a summary (total, needs a check, verified, corrected, AI agreement on checked labels) | P1 |
| `GET /api/labels/{labelId}` | One label with its subject, AI and final values, page and extraction links | P1 |
| `POST /api/labels/{labelId}/decision` | `{action: CONFIRM \| CORRECT, value?, note?, applyToSimilar?}`; writes an event; `CATEGORY` and `DOC_TYPE` changes mark months dirty; a run never overwrites it | P1 |
| `POST /api/labels/bulk-confirm` | Confirm up to 200 labels as proposed | P1 |
| `GET /api/dataset-exports` · `POST /api/dataset-exports` | Masked JSONL and BigQuery export of verified labels, owner only, with the workspace's consent (`403 CONSENT_REQUIRED`) and the minimum examples per task | later |

### 2.9 Worker (internal)

| Method & path | Caller | Body |
|---|---|---|
| `POST /tasks/process-document` | Cloud Tasks with an OIDC token for `kredibel-tasks-invoker` | `{orgId, docId, runId}` |
| `POST /tasks/reconcile-month` | Cloud Tasks (task name `month-{orgId}-{yyyy-mm}-{generation}`, 20 s delay) | `{orgId, month, generation, runId}` |

Both return `200` on success or when the run is already finished (idempotent), `5xx` to request a
retry, and `200 {"skipped": "superseded"}` when a newer generation exists for the month.

---

## 3. Errors

All errors use **RFC 9457** `application/problem+json`:

```json
{
  "type": "/problems/plan-limit-reached",
  "title": "Plan limit reached",
  "status": 403,
  "detail": "This file has 6 pages but only 4 of your 400 monthly pages are left.",
  "code": "PLAN_LIMIT_REACHED",
  "instance": "/api/documents",
  "limit": "extractedPagesPerMonth",
  "used": 396,
  "max": 400
}
```

| `code` | HTTP | When |
|---|---|---|
| `UNAUTHENTICATED` | 401 | Missing, invalid or expired token |
| `WORKSPACE_REQUIRED` | 403 | Signed in but no workspace yet |
| `ROLE_REQUIRED` | 403 | The caller's role may not do this (P1; `requiredRoles` included) |
| `SIGNUP_CLOSED` | 403 | `SIGNUP_MODE` is `closed`, or `invite_only` without an invite, or `MAX_WORKSPACES` reached |
| `ALREADY_IN_WORKSPACE` | 409 | Creating a workspace or accepting an invite while already in one |
| `TRIAL_EXPIRED` | 403 | Upload, month run or assistant question after the trial ended (`trialEndsAt` included); reads still work |
| `PLAN_LIMIT_REACHED` | 403 | A plan limit would be exceeded (`limit`, `used`, `max`) |
| `LANGUAGE_NOT_AVAILABLE` | 422 | A language marked `coming_soon` was requested |
| `NOT_FOUND` | 404 | Not found **or not in the caller's workspace** |
| `VALIDATION_ERROR` | 422 | Body or query invalid (`errors[]` lists fields) |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | Not PDF, PNG, JPEG, CSV or XLSX by content |
| `UPLOAD_IN_PROGRESS` | 409 | The same file is still being stored by another upload that has not finished within two minutes; try again |
| `DOCUMENT_TOO_LARGE` | 413 | Larger than `fileSizeMb` |
| `TOO_MANY_PAGES` | 422 | More pages than `pagesPerDocument` (`maxPages`, `splitAvailable` included) |
| `TOO_MANY_ROWS` | 422 | A ledger file with more rows than `ledgerRowsPerFile` |
| `ENCRYPTED_DOCUMENT` | 422 | Password-protected PDF |
| `ACTION_NOT_ALLOWED` | 422 | A resolve action that does not fit the item's kind (`allowedActions` included) |
| `ITEM_ALREADY_RESOLVED` | 409 | The review item is no longer `OPEN` |
| `MATCH_AMOUNT_MISMATCH` | 422 | A manual match whose two sides differ by more than the tolerance (`difference` included) |
| `ALREADY_MATCHED` | 409 | A record in a manual match is already fully matched (`matchIds` included) |
| `REASON_REQUIRED` | 422 | Ignore, dismiss or reopen without a reason (at least 10 characters) |
| `SUGGESTION_ALREADY_DECIDED` | 409 | Accepting or rejecting a suggestion that is no longer `PENDING`/`CONFLICT` |
| `MONTH_LOCKED` | 409 | A change to a signed-off month (P1) |
| `RUN_QUOTA_EXCEEDED` | 429 | `monthRunsPerDay` or the per-user rate limit reached (`retryAfterSeconds` included) |
| `RUNS_DISABLED` | 503 | New reading and runs switched off by `RUNS_ENABLED`; existing data stays readable |
| `LAST_OWNER` | 409 | Removing or demoting the last owner (P1) |
| `BANK_ACCOUNT_EXISTS` | 409 | Adding a bank account the workspace already has (same bank and number; `accountId` included) |
| `LABEL_VALUE_INVALID` | 422 | A label correction whose value is not in the task's vocabulary (`allowedValues` included) |
| `CONSENT_REQUIRED` | 403 | A dataset export while `learning.shareVerifiedLabels` is off |
| `DATASET_TOO_SMALL` | 422 | Fewer verified labels than `minExamplesPerTask` for a requested task (`counts` included) |
| `METHOD_NOT_ALLOWED` | 405 | The path exists but not with this HTTP method |
| `INTERNAL` | 500 | Unexpected; `detail` is generic, the log has the cause |

---

## 4. Review item actions

`POST /api/review-items/{itemId}/resolve` takes `{"action": …, …}`. Allowed actions per kind
([`08`](08-risk-engine.md) §7):

| Kind | Actions and their fields |
|---|---|
| `PROPOSED_MATCH` | `CONFIRM_MATCH` {`matchId`} · `MATCH` {`bankLineIds`, `invoiceIds?`, `receiptIds?`, `ledgerEntryIds?`} · `REJECT_MATCH` {`matchId`} |
| `UNMATCHED_BANK_LINE` | `MATCH` {…} · `NO_DOCUMENT_NEEDED` {`category`} · `IGNORE` {`reason`} |
| `UNMATCHED_DOCUMENT` | `MATCH` {…} · `NOT_YET_PAID` · `IGNORE` {`reason`} |
| `POSSIBLE_DUPLICATE` | `CONFIRM_DUPLICATE` · `NOT_DUPLICATE` |
| `LOW_CONFIDENCE_VALUE` | `CORRECT_VALUE` {`field`, `value`} · `ACCEPT_AS_READ` |
| `LEDGER_DIFFERENCE` | `EXPLAIN` {`note`} · `MATCH` {…} · `IGNORE` {`reason`} |
| `CONFIRM_TYPE` | `SET_TYPE` {`docType`} |
| `CONFIRM_LEDGER_MAPPING` | `CONFIRM_MAPPING` {`mapping`} (as proposed or edited) |

Every resolution is stored on the item (`resolution`), written to `events`, and marks the affected
months dirty; the month workflow then re-reconciles them. User decisions are inputs to
reconciliation and are never undone by a re-run ([`08`](08-risk-engine.md) §6.1).

---

## 5. Who may call what (P1 roles)

In P0 every member is `owner`. P1 roles map to actions like this (enforced by
`domain/access.py`, tested per endpoint):

| Action | owner | accountant | reviewer | viewer |
|---|:-:|:-:|:-:|:-:|
| Read everything in the workspace | ✓ | ✓ | ✓ | ✓ |
| Upload and delete documents, confirm type and ledger mapping | ✓ | ✓ | ✓ | |
| Match, unmatch, correct values, change categories | ✓ | ✓ | ✓ | |
| Decide duplicates, ignore items, explain ledger differences | ✓ | | ✓ | |
| Acknowledge or dismiss findings | ✓ | | ✓ | |
| Sign off and reopen months | ✓ | | ✓ | |
| Accept or reject profile suggestions, edit bank accounts | ✓ | | ✓ | |
| Ask the Finance Assistant | ✓ | ✓ | ✓ | ✓ |
| Confirm or correct labels | ✓ | ✓ | ✓ | |
| See the Runs page and agent events | ✓ | | | |
| Members, invites, workspace settings (incl. accounting framework, training consent), dataset exports | ✓ | | | |

---

## 6. Representative payloads

### Upload: an exact copy

```http
POST /api/documents
Content-Type: multipart/form-data; boundary=…
```

```json
{
  "docId": "doc_01JC2Q…",
  "fileName": "BCA_March_2026 (1).pdf",
  "status": "DUPLICATE",
  "duplicate": {"kind": "EXACT", "code": "D01_EXACT_FILE_DUPLICATE", "ofDocId": "doc_01JB7K…",
                "decision": "CONFIRMED"},
  "countsAgainstLimits": false
}
```

### Month

```json
{
  "month": "2026-03",
  "state": "NEEDS_REVIEW",
  "statements": [{"accountId": "acc_9f1c…", "accountMasked": "••••4821", "docId": "doc_01JB7K…"}],
  "figures": {
    "moneyIn": {"factId": "fact:2026-03:money_in", "value": {"amount": "231400000.00", "currency": "IDR"}},
    "moneyOut": {"factId": "fact:2026-03:money_out", "value": {"amount": "218900000.00", "currency": "IDR"}},
    "autoMatchRate": {"factId": "fact:2026-03:auto_match_rate", "value": "0.8667"}
  },
  "risk": {
    "level": "CRITICAL",
    "summary": "The March statement for ••••4821 was edited after it was created: on 14 March a credit of IDR 7,250,000 does not add up with the printed balance [[finding:fnd_7c1e…]].",
    "nextSteps": ["Download the March statement again from internet banking and upload it [[finding:fnd_7c1e…]]"],
    "reasons": ["fnd_7c1e09a2b3d4e5f6"],
    "grounding": "VERIFIED"
  },
  "openReviewItems": 2
}
```

### Review item: a proposed match

```json
{
  "itemId": "itm_51c0…",
  "kind": "PROPOSED_MATCH",
  "month": "2026-03",
  "status": "OPEN",
  "subject": {"bankLineIds": ["tx_3f2a…"]},
  "suggestion": {
    "candidates": [
      {"matchId": "mat_aa01…", "invoiceIds": ["inv_19d2…"], "score": "0.78",
       "reasons": ["AMOUNT_EXACT", "DATE_NEAR"], "text": "Same amount, paid 4 days after the invoice; client name differs"},
      {"matchId": "mat_aa02…", "invoiceIds": ["inv_77b0…"], "score": "0.71",
       "reasons": ["AMOUNT_EXACT", "PARTY_MATCH"], "text": "Same amount and client, paid 41 days after the invoice"}
    ]
  }
}
```

```json
{"action": "CONFIRM_MATCH", "matchId": "mat_aa02…"}
```

### Money flow (abridged)

```json
{
  "period": "2026-Q1",
  "nodes": [
    {"id": "src:client:cp_8e1d…", "column": "SOURCE", "label": "Harborview Hotel Group"},
    {"id": "acc:acc_9f1c…", "column": "ACCOUNT", "label": "Archipelago ••••4821"},
    {"id": "use:SUPPLIERS", "column": "USE", "label": "Suppliers"},
    {"id": "use:KEPT", "column": "USE", "label": "Kept in the account"}
  ],
  "links": [
    {"id": "lnk_2c4e…", "source": "src:client:cp_8e1d…", "target": "acc:acc_9f1c…",
     "value": {"amount": "182500000.00", "currency": "IDR"}, "lineCount": 9}
  ]
}
```

### Finding (abridged)

```json
{
  "findingId": "fnd_7c1e09a2b3d4e5f6",
  "code": "A01_RUNNING_BALANCE_BREAK",
  "category": "ARITHMETIC",
  "scope": "DOCUMENT",
  "docId": "doc_01JB7K…",
  "month": "2026-03",
  "severity": "CRITICAL",
  "title": "Running balance does not add up",
  "facts": {"previousBalance": "41250000.00", "credit": "7250000.00", "expectedBalance": "48500000.00",
            "printedBalance": "42500000.00"},
  "explanation": "On 14 March the statement adds a credit of IDR 7,250,000 but the printed balance rises by only IDR 1,250,000. Both readings agree on these values.",
  "nextSteps": ["Download the March statement again from internet banking and upload it"],
  "evidence": [{"docId": "doc_01JB7K…", "page": 2, "bbox": {"x0": 0.71, "y0": 0.42, "x1": 0.93, "y1": 0.45},
                "txId": "tx_3f2a…", "label": "Credit amount"}],
  "detectedBy": "RULE",
  "status": "OPEN"
}
```

### Assistant answer (P1)

```json
{
  "messageId": "msg_01JC…",
  "answer": {
    "parts": [
      {"type": "text", "text": "You paid Green Valley Farms IDR 96,400,000 in March across 3 transfers [[fact:q_5e1a:total]]. None of them went to a new account."},
      {"type": "table", "columns": ["Date", "Amount", "Account"], "rows": [["2026-03-05", "IDR 32,100,000", "••••0912"]]},
      {"type": "chart", "chart": "MONEY_FLOW", "query": {"period": "2026-03", "counterpartyId": "cp_31aa…"}}
    ],
    "citations": [{"ref": "fact:q_5e1a:total", "label": "Payments to Green Valley Farms, March 2026"}],
    "grounding": "VERIFIED"
  }
}
```
