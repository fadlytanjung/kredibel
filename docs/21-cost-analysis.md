# 21 — Cost Analysis & Database Options

> What Kredibel costs to run during the competition, which database fits the requirements at the
> lowest cost, and the guardrails that keep spend predictable.
> Prices are **list prices checked on 10 Oct 2026**, mostly for `us-central1`; Singapore
> (`asia-southeast1`) is usually somewhat higher. ⚠️ Confirm every figure in the
> [Google Cloud pricing calculator](https://cloud.google.com/products/calculator) before relying on it.

---

## 1. Summary

| Question | Answer |
|---|---|
| Which database? | **Firestore (Standard edition, Native mode, the single `(default)` database)**. It meets every data requirement, and its daily free quota covers our expected workload: about **USD 0** for the competition. |
| What about Cloud SQL for PostgreSQL? | It works, but it is always-on: **≈ USD 9–17/month** for the smallest shared-core instance (no SLA, 0.6 GiB RAM), **≈ USD 50/month** for 1 dedicated vCPU. It also has no realtime push, so the UI would need polling or a second store. Not worth it for this workload. |
| What actually drives cost? | **Reading pages with AI** and the memo, not the database. |
| How do we read documents? | **Adaptive reading** ([ADR-010](adr/ADR-010-adaptive-extraction-ai-reader-and-witness.md)): Gemini reads each page image; the PDF text layer (free) or Document AI OCR (USD 1.50 per 1,000 pages, scans only) is the independent witness. Document AI parsers are used only to escalate a doubtful page. |
| Cost per new case (scenario S1, 28 pages) | **≈ USD 0.34** if every page is digital, **≈ 0.38** if every page is scanned. The previous dual design cost **≈ USD 1.9** (Form Parser + Invoice Parser + Gemini) or **≈ 5.8** (Bank Statement Parser). Re-running the same documents costs **≈ USD 0.17** thanks to the page cache. |
| Expected competition spend (10 Oct – 4 Dec) | **≈ USD 50–70** including public free trials during judging (+15% buffer ≈ **80**), with the guardrails in §5. |
| Worst case per free-trial workspace | Capped by the plan at **USD 5 of estimated AI spend per month** ([`contracts/plans.v1.yaml`](../contracts/plans.v1.yaml)); `MAX_WORKSPACES` caps the number of workspaces. |

---

## 2. Database options

### 2.1 What the data layer must do

From [`03`](03-prd.md), [`05`](05-architecture.md) and [`09`](09-data-model.md):

| # | Requirement | Why |
|---|---|---|
| D1 | Push live progress to the browser (≤ 2 s) | NFR-02; live pipeline is a demo moment |
| D2 | Hierarchical, per-case data: documents, ~400 transactions, findings, analysis, memo, events | Data model |
| D3 | Atomic state change + audit event | FR-046, constitution P5 |
| D4 | Org isolation in the backend **and** for direct client reads | NFR-06 |
| D5 | Simple filters and ordering (by month, category, severity), cursor pagination | API |
| D6 | Scale to zero; no capacity planning; no VPC work | 7-day build; cost limit |
| D7 | Near-zero cost at demo volume | Budget |

Cross-case analytics (portfolio views) are **P2** and belong in an analytical store, not the
operational one.

### 2.2 Options compared

| Option | Smallest realistic setup | Monthly cost (list) | D1 realtime | D3 atomic | D6 ops | Verdict |
|---|---|---|---|---|---|---|
| **Firestore Standard (Native)** | `(default)` database | **≈ USD 0**: free 50K reads, 20K writes, 20K deletes and 1 GiB per day; then USD 0.03 / 0.09 / 0.01 per 100K reads/writes/deletes | ✅ native listeners | ✅ transactions | ✅ serverless | **Chosen** |
| Cloud SQL for PostgreSQL, `db-f1-micro` (shared core) | 0.6 GiB RAM, 10 GiB SSD | ≈ USD 7.7 compute + 1.7 storage; + ≈ 7.3 if it holds a public IPv4 → **≈ USD 9–17** | ❌ (poll or add a channel) | ✅ | ⚠️ connector/IP, migrations, pool limits; no SLA | Fallback only |
| Cloud SQL `db-g1-small` | 1.7 GiB RAM | ≈ USD 25.6 + storage | ❌ | ✅ | ⚠️ | Not needed |
| Cloud SQL dedicated 1 vCPU / 3.75 GiB | — | ≈ USD 49 + storage (HA doubles it) | ❌ | ✅ | ⚠️ | Not needed |
| AlloyDB for PostgreSQL | 2 vCPU / 16 GiB primary | ≈ USD 227+ | ❌ | ✅ | ⚠️ VPC required | Too expensive |
| Spanner (granular, 100 processing units) | regional | from ≈ USD 40+ | ❌ | ✅ | ✅ | Over-built for this |
| BigQuery | — | free tier: 10 GiB storage, 1 TiB queries | ❌ | ❌ (analytical) | ✅ | P2 analytics export only |
| Firestore Enterprise (MongoDB compatibility) | — | free tier exists; unit-based pricing | ✅ | ✅ | ✅ | No benefit over Standard here |

```mermaid
%%{init: {"theme": "base", "themeVariables": {"fontFamily": "Arial, Helvetica, sans-serif", "fontSize": "14px", "xyChart": {"plotColorPalette": "#0F5E56", "backgroundColor": "#FFFFFF"}}}}%%
xychart-beta
    title "Minimum monthly DB cost (USD)"
    x-axis ["Firestore", "SQL f1-micro", "SQL g1-small", "SQL 1 vCPU", "Spanner 100PU", "AlloyDB"]
    y-axis "USD per month" 0 --> 240
    bar [0, 17, 27, 51, 40, 227]
```

Sources for the figures: §8.

### 2.3 Our workload against the Firestore free quota

Estimated for one full S1 run plus one analyst review session:

| Operation | Count | Notes |
|---|---|---|
| Writes | ~1,000 | ~360 transactions written twice (consensus, then categories), ~130 document status updates, ~100 debounced progress/stage updates, findings, invoices, analysis, memo, events |
| Reads | ~1,500 | Pipeline reads of transactions/findings plus UI listener updates and tab loads |
| Storage | < 5 MB per case | Files live in Cloud Storage, not Firestore |

The free quota (20,000 writes/day) covers **~20 full runs per day**. Every run beyond that costs about
**USD 0.001** in Firestore operations. The free tier applies to **one database per project**, which is
why we use only `(default)` (ADR-003).

### 2.4 If the team still wants PostgreSQL

Use it **only** if a hard requirement appears (complex ad-hoc SQL, an existing Postgres skill set the
team insists on). Then:

1. `db-f1-micro`, Enterprise edition, single zone, 10 GiB SSD, no HA. Accept no SLA.
2. Connect from Cloud Run with the **Cloud SQL connector and IAM database auth**. Use a public IP
   (≈ USD 7/month) or private IP through **Direct VPC egress**; avoid a Serverless VPC Access
   connector (extra always-on instances).
3. Keep each service's connection pool small (≤ 5) because the micro instance allows few connections.
4. **Stop the instance** outside working hours (`gcloud sql instances patch --activation-policy=NEVER`)
   to pay only for storage while it's stopped.
5. Keep **Firestore for the live progress channel** anyway (or switch the UI to 3-second polling), so
   D1 still holds. That means two stores: one more reason to stay on Firestore alone.
6. Bonus: Postgres would let ADK use its `DatabaseSessionService` for assistant sessions.

---

## 3. Per-case cost model

### 3.1 Prices used

| Service | Price used | Source |
|---|---|---|
| Document AI Enterprise Document OCR | **USD 1.50 per 1,000 pages** (USD 0.60 above 5M pages/month) | Document AI pricing |
| Document AI Form Parser | USD 30 per 1,000 pages | Document AI pricing |
| Document AI Invoice Parser | USD 0.10 for every 10 pages in a document | Document AI pricing |
| Document AI Bank Statement Parser | USD 0.75 per classified document | Document AI pricing |
| Document AI Layout Parser / Custom Extractor | USD 10 / USD 30 per 1,000 pages | Document AI pricing (not used; for comparison) |
| Document AI free tier | none listed (the USD 300 new-customer credit applies) | Document AI pricing |
| `gemini-3.8-flash` | USD 0.75 in / 3.75 out per 1M tokens (introductory to 31 Dec 2026) | third-party price tracker |
| `gemini-3.5-flash-lite` | USD 0.30 in / 2.50 out per 1M tokens | third-party price tracker |
| `gemini-3.1-pro-preview` | USD 2 in / 12 out per 1M tokens (≤ 200K context) | third-party price tracker |
| Gemini image input | **1,120 tokens per image** at media resolution `high` (2,240 at `ultra_high`); native PDF input is 560 tokens per page at `medium` | Gemini media-resolution docs |
| Model Armor (standalone) | 2M tokens/month free, then USD 0.10 per 1M | Security Command Center pricing |
| Cloud Run | free 180K vCPU-s, 360K GiB-s, 2M requests per month | Cloud Run pricing |
| Cloud Tasks | first 1M operations/month free | Cloud Tasks pricing |

### 3.2 Cost per page, by reading method

| Method | Statement page (~25 rows) | Invoice page |
|---|---|---|
| **AI reader:** Gemini Flash on the page image | **≈ USD 0.0069** | **≈ USD 0.0034** |
| **Witness:** PDF text layer (digital pages) | USD 0 | USD 0 |
| **Witness:** Document AI Enterprise OCR (scanned pages) | USD 0.0015 | USD 0.0015 |
| Escalation: Form Parser | USD 0.030 | USD 0.030 |
| Escalation: Invoice Parser | — | USD 0.10 (1–10 pages) |
| Bank Statement Parser (not used) | USD 0.75 per document (≈ 0.25 per page for 3 pages) | — |

Token assumptions for one Gemini page read: 1,120 image tokens + ≈ 800 tokens of prompt, schema and
page-1 context in; ≈ 45 output tokens per statement row (≈ 1,225 per page) or ≈ 450 per invoice page,
plus 20% for thinking at the lowest setting. **E-PERF** ([`15`](15-testing-and-evaluation.md)) measures
the real numbers; replace these estimates with measurements once available.

### 3.3 Strategies compared, scenario S1 (18 statement pages, 10 one-page invoices)

"Rest of the run" is the same for every strategy: classification with Flash-Lite (≈ 0.014),
categorization with counterparty names (≈ 0.025), finding explanations (≈ 0.01) and the memo on Pro
(≈ 0.13, about 1.3 attempts): **≈ USD 0.18** (≈ 0.08 with the memo on Flash in development).

| Strategy | Reading pages | Rest of the run | **Total per case** | Independent check (P6) |
|---|---|---|---|---|
| A. Dual: Bank Statement Parser + Invoice Parser + Gemini | 4.50 + 1.00 + 0.16 | 0.18 | **≈ USD 5.8** | yes |
| B. Dual: Form Parser + Invoice Parser + Gemini (previous default) | 0.54 + 1.00 + 0.16 | 0.18 | **≈ USD 1.9** | yes |
| C. Document AI only (Form Parser + Invoice Parser) | 1.54 | 0.18 | **≈ USD 1.7** | no |
| D. Gemini only | 0.16 | 0.18 | **≈ USD 0.34** | no |
| **E. Adaptive, all pages digital (chosen)** | 0.16 + 0 | 0.18 | **≈ USD 0.34** | **yes** |
| E′. Adaptive, all pages scanned | 0.16 + 0.04 | 0.18 | **≈ USD 0.38** | yes |
| F. Adaptive + escalating 10 statement pages (P1, worst case) | 0.16 + 0.30 | 0.18 | **≈ USD 0.64** | yes, 3 sources on those pages |
| G. Thorough mode (evals; future paid tier) | 0.16 + 0.54 + 1.00 | 0.18 | **≈ USD 1.9** | yes, 3 sources everywhere |

D and E cost the same because the text-layer witness is free; E adds the independent check that a
fraud verdict needs. That is the whole argument for the adaptive design.

```mermaid
%%{init: {"theme": "base", "themeVariables": {"fontFamily": "Arial, Helvetica, sans-serif", "fontSize": "14px", "xyChart": {"plotColorPalette": "#0F5E56", "backgroundColor": "#FFFFFF"}}}}%%
xychart-beta
    title "Cost per new S1 case by strategy (USD)"
    x-axis ["Dual BSP", "Dual Form", "DocAI only", "Adaptive", "Adaptive scan", "Adaptive esc"]
    y-axis "USD per case" 0 --> 6
    bar [5.8, 1.9, 1.7, 0.34, 0.38, 0.64]
```

### 3.4 Heavier applicants

Costs scale with pages, so the gap grows with document volume. An applicant with six 20-page
statements (120 pages) and 30 one-page invoices:

| Strategy | Reading | Total per case |
|---|---|---|
| B. Dual, Form Parser + Invoice Parser + Gemini | 3.60 + 3.00 + 0.93 | **≈ USD 7.7** |
| E. Adaptive, digital | 0.93 | **≈ USD 1.1** |
| E′. Adaptive, scanned | 0.93 + 0.23 | **≈ USD 1.3** |

### 3.5 Where the money goes in the chosen design

```mermaid
%%{init: {"theme": "base", "themeVariables": {"fontFamily": "Arial, Helvetica, sans-serif", "fontSize": "14px", "pie1": "#0F766E", "pie2": "#1D4ED8", "pie3": "#B45309", "pie4": "#7C3AED", "pie5": "#64748B", "pieSectionTextColor": "#FFFFFF", "pieStrokeColor": "#FFFFFF", "pieOuterStrokeColor": "#FFFFFF"}}}%%
pie showData
    title New S1 case, adaptive reading (US cents)
    "Memo (Pro)" : 13
    "AI reading, statements" : 12.4
    "AI reading, invoices" : 3.4
    "Categorize + explain" : 3.5
    "Classify (Flash-Lite)" : 1.4
```

### 3.6 Decisions

- **`EXTRACTION_MODE=adaptive`** is the default for every plan; `thorough` is for evals and a future
  paid tier (shown as "coming soon").
- **Per page, not per document:** pages are the unit of reading, caching, escalation and plan
  accounting; Document AI's online page limits stop mattering because no request exceeds 15 pages.
- **Specialized Document AI parsers only on demand** (escalation, P1). The Bank Statement Parser is not
  used: at USD 0.75 per document it costs more than reading a whole case adaptively.
- **Gemini reads images, not the PDF:** native PDF input would be ≈ USD 0.0004 cheaper per page but
  would show the model the text layer and remove the witness's independence.
- **Spike S1** confirms the per-page token counts, Gemini's field accuracy on page images (`high` vs
  `ultra_high`), and the verifier's agreement on S1–S3 and a scanned variant.

---

## 4. Competition budget (10 Oct – 4 Dec 2026)

Assumes the page cache (§5), recordings for tests, and Flash for the memo during development.

| Bucket | Volume | Estimate |
|---|---|---|
| Unique documents read (S1–S6 × 5 seeds + scanned variants; shared files are cached) | ≈ 166 statement pages, 82 invoice pages, 40 of them scanned | ≈ USD 2 |
| Spike S1 and escalation/thorough evals (Form Parser, Invoice Parser on S1–S3) | ≈ 60 statement pages, 30 invoices | ≈ USD 5 |
| Development runs (cached extraction, Flash memo) | ~150 runs | ≈ USD 8–10 |
| Eval runs (Gemini cache bypassed, Pro memo) | ~60 cases | ≈ USD 20 |
| Demo and judging (seeded cases + some new uploads) | ~50 runs, ≤ 15 new cases | ≈ USD 10–12 |
| Public free trials during judging (`MAX_WORKSPACES=15`, most stay small) | realistic: 10 trials × ~100 pages, a few runs each | ≈ USD 5–15 (hard cap 15 × USD 5/month) |
| Infrastructure (Cloud Run, Storage, Artifact Registry, Build, Logging, Firestore) | 2 months | ≈ USD 3–8 |
| **Total** | | **≈ USD 50–70** (+15% buffer ≈ **80**) |
| Add Cloud SQL instead of Firestore | | + ≈ USD 20–35 (micro, 2 months) or + ≈ USD 100 (1 vCPU) |

For comparison, the previous dual design cost ≈ USD 55–80 **without** public trials; adaptive reading
pays for opening the free trial to judges.

New Google Cloud customers get **USD 300 in free credits** (per the Cloud SQL pricing page). If a team
member's billing account qualifies, the whole competition fits inside the credit. Check before
creating the project.

---

## 5. Cost controls built into the design

| Control | Where | Effect |
|---|---|---|
| **Adaptive reading** | One AI reading per page; free text-layer witness; OCR only for scans ([`07`](07-document-intelligence.md) §5) | ≈ 5× cheaper per case than dual parsers |
| **Page triage** | Blank pages skipped; unusable text layers routed to OCR, not to a second AI | No paid call for empty pages |
| **Page-level extraction cache** | `orgs/{orgId}/cache/extraction/{sha256}/p{n}/…` ([`09`](09-data-model.md) §7) | Re-uploading demo files costs nothing to read; cache hits don't count against plan pages |
| **Escalation budget** (P1) | `escalationPagesPerCase` (10) and `EXTRACTION_ESCALATION` | Parser spend per case is bounded |
| **Plan entitlements** | `contracts/plans.v1.yaml`: pages/month, runs/day, cases/month, **AI spend per month** ([`specs/013`](specs/013-workspace-and-plans/spec.md)) | One workspace can't run up the bill |
| **Sign-up controls** | `SIGNUP_MODE` (`open`, `invite_only`, `closed`), `MAX_WORKSPACES` | Bounds the number of free trials |
| **Recorded outputs for tests** | `backend/tests/scenarios/recordings/` ([`15`](15-testing-and-evaluation.md) §5) | CI and `make check` never call paid services |
| **Model per environment** | `MODEL_REASONING=gemini-3.8-flash` in local/dev; Pro only for demo and evals | Memo cost ÷ 4 during development |
| **Thinking kept low** | Classification, reading and categorization use the lowest thinking setting | Fewer billed output tokens |
| **Run quotas** | `RUN_QUOTA_PER_ORG_PER_DAY` (default 30) and per-user rate limit (5/min); `429 RUN_QUOTA_EXCEEDED` | Global ceiling above plan limits |
| **Kill switch** | `RUNS_ENABLED=false` → `503 RUNS_DISABLED`; existing results stay readable | Instant stop without taking the demo down |
| **Scale to zero** | Cloud Run min instances 0 (1 only while recording the video) | No idle compute |
| **Budget alerts** | Budget = team limit, alerts at 50% / 90% / 100% to the team email | Early warning |
| **Artifact Registry cleanup** | Keep the 3 most recent images | Storage stays under the free 0.5 GB or close to it |
| **Log hygiene** | No document content in logs; default retention | Stays within the 50 GiB free logging allotment |
| **Lifecycle on the bucket** | Delete objects after 90 days | Storage doesn't accumulate |

---

## 6. What we deliberately did not choose, for cost reasons

| Option | Why not |
|---|---|
| Always-on databases (Cloud SQL, AlloyDB, Spanner) | Pay 24/7 for a workload that is idle most of the day |
| Two paid readers on every page (ADR-004 as default) | ≈ 5× the cost of adaptive reading for the same corroboration |
| Bank Statement Parser | USD 0.75 per document, more than a whole adaptive case |
| Gemini Batch prediction (≈ 50% cheaper) | Asynchronous with long turnaround; an analysis must finish in ≤ 3 minutes |
| Agent Runtime for the pipeline | Extra always-on/compute billing; Cloud Run's free tier covers our runs (ADR-002) |
| Firebase Hosting + CDN | Not needed at demo scale; one Cloud Run service serves the SPA (ADR-008) |
| Serverless VPC Access connector | Always-on connector instances; nothing in our design needs a VPC |
| Gemini Pro for every call | Flash/Flash-Lite are sufficient for reading and categorizing; Pro only writes the memo |

---

## 7. Spend checklist (owner: role D)

- [ ] Billing account linked; check eligibility for the USD 300 new-customer credit.
- [ ] Budget created with alerts at 50/90/100% (day 0).
- [ ] Spike S1 done: `EXTRACTION_MODE=adaptive` confirmed, media resolution chosen, per-page token counts recorded.
- [ ] Enterprise OCR processor created in `us` (`DOCAI_OCR_PROCESSOR_ID`); Form/Invoice Parser processors only if escalation is built.
- [ ] `MODEL_REASONING` set to Flash in `infra/env.*.yaml` until the demo build.
- [ ] Trial limits in `contracts/plans.v1.yaml` reviewed; `SIGNUP_MODE` and `MAX_WORKSPACES` set before sharing the link.
- [ ] `RUN_QUOTA_PER_ORG_PER_DAY` set before sharing the prototype link.
- [ ] Artifact Registry cleanup policy applied.
- [ ] After the video: min instances back to 0.
- [ ] After judging ends: set `RUNS_ENABLED=false` and `SIGNUP_MODE=closed`, or delete the project.

---

## 8. Sources

- [Cloud SQL pricing](https://cloud.google.com/sql/pricing)
- [Firestore pricing](https://firebase.google.com/docs/firestore/enterprise/pricing), [Firestore quotas](https://docs.cloud.google.com/firestore/quotas)
- [Document AI pricing](https://cloud.google.com/document-ai/pricing) (checked 10 Oct 2026: Enterprise OCR, Form Parser, Invoice Parser, Bank Statement Parser)
- [Gemini media resolution](https://ai.google.dev/gemini-api/docs/media-resolution) (image and PDF token counts)
- [Cloud Run pricing](https://cloud.google.com/run/pricing)
- [Model Armor pricing (Security Command Center pricing page)](https://cloud.google.com/security-command-center/pricing)
- Gemini model prices (third-party tracker, synced 8 Oct 2026): [benchlm.ai](https://benchlm.ai/google/api-pricing). Confirm on Google's pricing page.
- AlloyDB minimum (third-party): [Bytebase AlloyDB pricing](https://www.bytebase.com/dbcost/alloydb-pricing/)
- Spanner granular instances: [Google Cloud blog announcement](https://goo.gle/3AVJY27)
