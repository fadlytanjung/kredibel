# 02 — Research

> Facts this project depends on, where they came from, and what still needs confirming.
> Checked on **10 Oct 2026**. Anything marked ⚠️ must be re-verified before we rely on it.

---

## 1. The competition

### 1.1 Timeline

| Milestone | Date | Confidence |
|---|---|---|
| Registration & team formation closes | **11 Oct 2026** | ⚠️ Secondary source citing the official FAQ (checked 26 Sep 2026) |
| **Prototype submission closes** | **18 Oct 2026** | ⚠️ Same; time zone **not stated**, so treat 17 Oct as our real deadline |
| Evaluation | 19 Oct – 6 Nov 2026 | ⚠️ |
| Finalists announced | 7 Nov 2026 | ⚠️ |
| Grand Finale (Demo Day, Singapore, in person) | 4 Dec 2026 | Multiple sources agree |

Earlier listings showed a 3–4 Oct submission deadline; the extension to 18 Oct appears in sources
that cite the official FAQ. **Confirm both dates on the Hack2skill dashboard.**

### 1.2 Judging criteria

| Criterion | Weight |
|---|---|
| Technical Merit & Gen AI Implementation | 40% |
| Problem Alignment & Impact | 25% |
| Innovation & Creativity | 25% |
| User Experience & Solution Design | 10% |

### 1.3 Submission requirements (as published)

- A **proposal**: the solution, its impact, feasibility and scalability, aligned to the chosen theme.
- A **functional, working prototype**: not just a deck or mockup.
- A **3-minute demo video**, public link (YouTube, Vimeo or Google Drive).
- **Code, documentation and presentation in English.**
- A clear statement of the theme and problem addressed.

Our working copies live in [`../submission/`](submission).

### 1.4 Allowed technology

Published wording: build with **Gemini or Gemma** (or approved agentic platforms such as Agent
Platform, Antigravity, AI Studio) and deploy on **Google Cloud via Cloud Run or Firebase**.

**Our interpretation** (⚠️ confirm in the FAQ or with organizers):

- Every *managed service* and every *AI model* comes from Google Cloud or Firebase.
- Open-source libraries running inside our own containers are allowed (FastAPI, React, pikepdf,
  pdfplumber, reportlab, etc.).
- No third-party AI APIs, vector databases, auth providers or hosting.

### 1.5 Eligibility (relevant to the team)

Working professionals aged 21+, JAPAC region, teams of 2–4, **no students**. Eligibility can be
checked at any stage.

### 1.6 Prizes

USD 30,000 total. Winner USD 10,000; runners-up USD 7,000 and 5,000; special awards of USD 2,000
each: Best Use of Google Cloud AI Tools, Most Impactful Solution, Social Choice, Best UI/UX.
Kredibel is designed to compete for **Best Use of Google Cloud AI Tools** as well (Document AI +
Gemini + ADK + Model Armor + Agent Platform Sessions).

---

## 2. Google Cloud facts we build on

### 2.1 Naming (2026 rename)

Vertex AI is now **Gemini Enterprise Agent Platform** ("Agent Platform"). Names used in these docs:

| Old name | Current name |
|---|---|
| Vertex AI API | Gemini Enterprise Agent Platform API |
| Vertex AI Agent Engine | Agent Runtime on Gemini Enterprise Agent Platform |
| Agent Engine Sessions / Memory Bank | Gemini Enterprise Agent Platform Sessions / Memory Bank |
| Gen AI evaluation service | Gemini Enterprise Agent Platform Evals |
| Vertex AI Search | Agent Search |

⚠️ The rename page does not say whether SDK package names or API hostnames changed. We use the
`google-genai` SDK with `GOOGLE_GENAI_USE_VERTEXAI=TRUE`, which is what ADK uses. Verify in spike S2.

### 2.2 Gemini models (Agent Platform, global endpoint)

| Role in Kredibel | Model ID | Status |
|---|---|---|
| Fast multimodal work: page and receipt reading, month explanations, assistant, visual forensics | `gemini-3.8-flash` | Listed, not marked preview |
| Bulk, cheap work: classification, ledger column mapping, categorization | `gemini-3.5-flash-lite` | Listed, not marked preview |
| Embeddings for assistant retrieval (P1) | `gemini-embedding-001` at 768 dimensions (`gemini-embedding-2` to compare) | Listed |
| DeepEval judge (evals only) | a Gemini model on Agent Platform (`EVAL_JUDGE_MODEL`) | — |

Model IDs are **configuration** (`MODEL_FAST`, `MODEL_LITE`, `MODEL_EMBEDDING`), never hard-coded.
The location is `global`. ⚠️ Confirm availability in Model Garden for our project on day 0.

### 2.3 Agent Development Kit (ADK)

- Latest Python release **2.11.0 (2 Oct 2026)**; Python ≥ 3.10. ADK 2.0 went GA for Python on 19 May
  2026.
- ADK 2.0 adds **graph workflows**: `Workflow(name=..., edges=[...])`. Nodes are `Agent`s or
  plain functions; routing via `Event(route=...)`; fan-out/fan-in with `JoinNode`
  (`google.adk.workflow`).
- **Dynamic workflows:** a `@node(rerun_on_resume=True)` orchestrator calls
  `await ctx.run_node(child, input)` in ordinary Python loops; parallelism with `asyncio.gather`.
- **Human input:** a node yields `RequestInput(message=..., payload=..., response_schema=...)`
  (`google.adk.events`) to pause. We do **not** pause workflows: anything that needs a person becomes
  a review item and a new run ([`06`](06-agent-design.md) §9).
- Agents in a graph run in `single_turn` (default) or `task` mode and accept Pydantic
  `input_schema` / `output_schema`.
- `Event(state={...})` writes session state; the docs advise against putting large payloads in
  state (use artifacts or a database). **We persist all large data in Firestore/GCS.**
- Resumability: `App(..., resumability_config=ResumabilityConfig(is_resumable=True))`; tools may run
  more than once on resume, so **side-effecting nodes must be idempotent**.
- CLI: `adk web`, `adk run`, `adk eval`, `adk deploy cloud_run`. Extras include `eval`, `otel-gcp`,
  `gcp`, `db`.
- Breaking change from 1.x: custom overrides of `_run_async_impl()` are ignored. Use callbacks.

### 2.4 Document AI

Prices checked on 10 Oct 2026 on the Document AI pricing page; no Document AI free tier is listed.

| Processor | Stable version we target | Online page limit | Regions | Notes |
|---|---|---|---|---|
| **Enterprise Document OCR** | v2 | 15 | many incl. `us` | **USD 1.50 per 1,000 pages** (USD 0.60 above 5M/month); words with bounding polygons; **the witness for scanned pages** ([ADR-010](adr/ADR-010-adaptive-extraction-ai-reader-and-witness.md)) |
| Form Parser | v2.0 | 15 | many incl. `us` | USD 30 per 1,000 pages; tables with cell boxes; escalation and thorough mode only (P1) |
| Invoice Parser | v2.0 (2023-12-06) | 10 (sync) | `us`, `eu`, `asia-southeast1`, … | USD 0.10 for every 10 pages in a document; escalation and thorough mode only (P1) |
| Bank Statement Parser | `pretrained-bankstatement-v5.0-2023-12-06` | 15 | `us`, `eu` | USD 0.75 per classified document; **not used** (cost, [`21`](21-cost-analysis.md) §3.6) |
| Expense Parser (receipts) | v1.4.2 (2024-09-12) | 10 | `us`, `eu`, `asia-southeast1`, … | Not used: receipts are read by Gemini with an OCR witness; a candidate for P1 escalation |
| Custom Classifier | v1.5 GA (zero-shot) | 15 | many incl. `asia-southeast1` | Optional; we classify with Gemini first |
| Custom Extractor (generative) | v1.5 / v1.5-pro GA; Gemini 3.x-based versions in preview | 15 | US, EU, `asia-southeast1` (generative) | Production path for data residency (see ADR-009) |
| Layout Parser | v1.0 | 15 | `us`, `eu` | Fallback for table structure, P2 |

Legacy processors (mortgage, utility, 1099 etc.) were discontinued on 30 Jun 2026. None of them are
in our design.

**Gemini input tokens for documents (media-resolution docs):** an image costs 280 / 560 / 1,120 /
2,240 tokens at `low` / `medium` / `high` / `ultra_high`; a PDF page costs 560 at the default (`medium`,
plus native text). Google recommends `medium` for PDFs and `high` for images. We send page images at
`high` so the AI never sees the text layer (independence from the witness).

### 2.5 Model Armor

- Sanitizes prompts and responses through templates with filters for **prompt injection &
  jailbreak**, malicious URIs, responsible-AI categories and Sensitive Data Protection.
- **Accepts files directly** (base64 with a byte data type, e.g. PDF), so we can screen an uploaded
  document *before any model reads it*.
- Requires a **regional endpoint**: `modelarmor.{LOCATION}.rep.googleapis.com`.
- Python client: `google-cloud-modelarmor` (`modelarmor_v1`). The result exposes
  `sanitization_result.filter_match_state` (`MATCH_FOUND` / `NO_MATCH_FOUND`) and per-filter
  results.

### 2.6 Assistant, retrieval, traces and evaluation (checked 10 Oct 2026)

| Building block | What we rely on | Used in |
|---|---|---|
| **Memory Bank** | ADK `VertexAiMemoryBankService(project, location, agent_engine_id)` with `PreloadMemoryTool` (memories added to the instruction at the start of a turn) or `LoadMemoryTool`; `add_events_to_memory` (recommended, incremental) or `add_session_to_memory` from a callback; memories scoped by user ID and app name and consolidated in the background; works with an agent running on Cloud Run; a Memory Bank can be created without deploying code (`client.memory_banks.create()`) | [ADR-014](adr/ADR-014-finance-assistant-tools-rag-memory.md), spec 011 |
| **Sessions** | `VertexAiSessionService(project, location, agent_engine_id)` with a Sessions instance ID; any ADK session service works | spec 011 |
| **RAG Engine** | Managed RAG corpora; the default `RagManagedDb` runs on Spanner with tiers (Basic = 100 processing units), so it has a fixed monthly cost | Not chosen for P1 ([ADR-014](adr/ADR-014-finance-assistant-tools-rag-memory.md)) |
| **Firestore vector search** | `find_nearest` with `EUCLIDEAN`, `COSINE` or `DOT_PRODUCT`; flat vector indexes; ≤ 2,048 dimensions; ≤ 1,000 results; a `where` pre-filter needs a composite vector index | Assistant retrieval ([`09`](09-data-model.md) §3.17) |
| **ADK traces** | Spans `invoke_agent`, `call_llm`, `generate_content`, `execute_tool`; export with `google_cloud.get_gcp_exporters(enable_cloud_tracing=True)` + `maybe_set_otel_providers`; outside Agent Runtime set `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false` to keep prompts and responses out of spans | [`17`](17-observability.md) |
| **DeepEval** | Open-source (Apache-2.0) evaluation library; `GeminiModel(model, project, location, temperature)` uses Gemini on Agent Platform as the judge; `deepeval set-gemini --model … --project … --location …` | [`15`](15-testing-and-evaluation.md) §5.1 |

⚠️ Memory Bank pricing: only third-party summaries were found (per GiB-month of storage and per
vCPU-hour of processing, with a small free tier, billed from 2026). Read the official pricing page
before enabling memory on the demo.

### 2.7 Antigravity (our coding agent)

- Reads **`AGENTS.md`** (or `GEMINI.md`) at the workspace root. These files take **no frontmatter**.
- Workspace rules: `.agents/rules/*.md` with required YAML frontmatter `trigger:` one of
  `always_on`, `model_decision`, `glob` (with `globs:`), `manual`. Files without valid frontmatter
  are **silently ignored**.
- Skills: `.agents/skills/<name>/SKILL.md` with `name` and `description`; invocable as `/<name>`.
- **Legacy workflows (`.agents/workflows/`) stop working on 19 Oct 2026.** We therefore put every
  repeatable procedure in **skills**, not workflows.
- Google's own SDD codelab pairs Antigravity with spec-kit: `specs/<feature>/spec.md → plan.md →
  tasks.md`, plus a constitution. Our feature specs use the same per-feature layout, but live in
  `docs/specs/` so that every SDD document sits under `docs/`. If the team adopts spec-kit, point its
  specs directory there (or symlink `specs → docs/specs`).

---

## 3. Market & problem evidence

| Claim | Figure | Source quality |
|---|---|---|
| SME funding gap in Southeast Asia | ~USD 300 billion | Secondary (press article, 2020); original report not named. Use as "frequently cited estimate". |
| SMEs' share of GDP, ASEAN-5 | 42% | Deloitte study (2015), via the same article. Dated. |
| Share of documents flagged as manipulated (one vendor's network, 2025) | ~6% (≈1 in 16) | Vendor-reported (Inscribe, 2026). |
| Fraud leaders naming bank statements the most vulnerable document | 85.6% of 90 surveyed | Vendor survey (Inscribe, 2026). |
| Altered documents that changed financial data (balances, deposits, transactions) | 91.2% in 2025 | Vendor-reported. |
| Template-based fakes | ~1 in 5 flagged documents in 2025, up from 1 in 14 in 2024; templates sell for as little as USD 10 | Vendor-reported. |
| Growth in AI-generated documents flagged | ~4× from Jun 2025 to May 2026 | Vendor-reported. |
| Business email compromise (payment diversion) losses reported to the FBI | ≈ USD 2.8 billion in 2024; ≈ USD 8.5 billion over 2022–2024 | FBI IC3 2024 Annual Report, via Nacha (2025). US data only. |

**How to use these in the pitch:** state them as reported by their source; do not combine them into
a market-size claim of our own. The SME figures describe how many businesses exist and how thin their
finance teams are; the fraud figures describe what goes wrong with documents and payments.

### 3.1 Domain anchors we design against

- **IAS 7 *Statement of Cash Flows*** classifies cash flows as operating, investing or financing.
  Indonesia's equivalent is **PSAK 207** (formerly PSAK 2) after the IAI renumbering. Kredibel's
  categorization taxonomy follows these classes.
- **Bank reconciliation practice:** each month, bank lines are matched to the books (invoices,
  receipts, ledger cash entries); differences are explained or corrected before the month is closed.
  Kredibel automates the matching and keeps the explanation and correction with a person.
- **Payment-diversion controls:** a change to a supplier's bank account is confirmed through a known
  phone number before paying. Kredibel flags a payment to an account not seen before for that
  supplier (`X08`).
- **Regulatory context for production (not the prototype):** Indonesia's Personal Data Protection Law
  (Law No. 27 of 2022) and record-keeping rules for accounting documents. ⚠️ Have a compliance
  reviewer confirm before any real-data pilot. The prototype uses synthetic data only.

---

## 4. Lessons carried over from our previous projects

| From | Lesson | Where it lands |
|---|---|---|
| Previous financial platform | Broad scope dilutes the demo | Scope guardrails, [`01`](01-brainstorm-and-decision.md) §6 |
| Contact-centre multi-agent project | Behaviour belongs in prompt files, not Python; evals are separate from the merge gate; trajectory evals find silent tool failures | [`06`](06-agent-design.md), [`15`](15-testing-and-evaluation.md) |
| Previous Google Cloud hackathon entry | Firestore rules: deploy with `--only firestore` and verify the released ruleset; no secrets in images; the server verifies Firebase ID tokens itself | [`14`](14-security-and-compliance.md), [`16`](16-infrastructure-and-deployment.md) |
| Real-time quiz project | Specs-first numbering, repository layer, acceptance-criteria-named tests | [`13`](13-design-patterns-and-conventions.md) |

---

## 5. Spikes to run on day 0 (time-boxed)

Each spike answers one question and records the result in this file (§6).

| ID | Question | Time-box | Decides |
|---|---|---|---|
| **S1** | Reading pages as images: how accurate is Gemini Flash on S1 statement, invoice and receipt images at media resolution `high` vs `ultra_high`, how many tokens per page, and what agreement does the verifier reach against the text layer? | 1.5 h | `READ_MEDIA_RESOLUTION`, verifier thresholds, cost per page ([`07`](07-document-intelligence.md) §5–§6, [`21`](21-cost-analysis.md) §3) |
| **S2** | Does ADK 2.11 run a `Workflow` with a dynamic `@node` orchestrator inside FastAPI on Cloud Run, calling Gemini on the Agent Platform global endpoint via ADC, with spans in Cloud Trace? | 1.5 h | [`06`](06-agent-design.md) as written, or the fallback to plain asyncio orchestration |
| **S3** | Enterprise OCR on the scanned S1 variant and on receipt photos: box quality, orientation, latency | 45 min | OCR witness settings; receipt tolerance |
| **S4** | Does Model Armor flag our synthetic "hidden instruction" invoice when the PDF is sent as a file? Which location works for our project? (P1) | 45 min | Screening node design, scenario S6 |
| **S5** | Sessions and Memory Bank from Cloud Run without deployed agent code: one instance or two, region, custom memory topics, `PreloadMemoryTool` latency (P1) | 1 h | ADR-014 details, spec 011 |
| **S6** | Does `gemini-3.8-flash` return usable `box_2d` boxes for a suspicious region on a rendered statement page? (P1) | 45 min | Visual forensics |

---

## 6. Spike results

_To be filled in on day 0._

| ID | Result | Consequence |
|---|---|---|
| S1 | | |
| S2 | | |
| S3 | | |
| S4 | | |
| S5 | | |
| S6 | | |

---

## 7. Sources

- AI Builder Cup listings (timeline, criteria, requirements, prizes):
  [opportunitiescircle.com](https://www.opportunitiescircle.com/google-cloud-ai-builder-cup/),
  [thestartupopportunity.com](https://www.thestartupopportunity.com/opportunities/ai-builder-cup),
  [deadline update citing the official FAQ](https://github.com/williamlabdev/context-rail/pull/9),
  official site [aibuildercup.com](https://aibuildercup.com/)
- ADK: [ADK 2.0 overview](https://adk.dev/2.0/), [graph workflows](https://adk.dev/graphs/),
  [routes & join](https://adk.dev/graphs/routes/), [data handling](https://adk.dev/graphs/data-handling/),
  [dynamic workflows](https://adk.dev/graphs/dynamic/), [human input](https://adk.dev/graphs/human-input/),
  [resume](https://adk.dev/runtime/resume/), [PyPI google-adk](https://pypi.org/project/google-adk/)
- Gemini models: [Gemini API models](https://ai.google.dev/gemini-api/docs/models),
  [Agent Platform locations](https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/locations)
- Rename: [Agent Platform name changes](https://docs.cloud.google.com/gemini-enterprise-agent-platform/vertex-ai-name-changes)
- Document AI: [processor list](https://docs.cloud.google.com/document-ai/docs/processors-list),
  [release notes](https://docs.cloud.google.com/document-ai/docs/release-notes)
- Model Armor: [sanitize prompts and responses](https://docs.cloud.google.com/model-armor/sanitize-prompts-responses)
- Antigravity: [rules](https://antigravity.google/docs/rules/), [skills](https://antigravity.google/docs/skills/),
  [workflows → skills migration](https://antigravity.google/docs/migration/workflows-to-skills/),
  [SDD with Antigravity and spec-kit (codelab)](https://codelabs.developers.google.com/sdd-adk-antigravity)
- Market: [SME funding gap article](https://www.crowdfundinsider.com/2020/07/164576-300-billion-funding-gap-for-smes-in-southeast-asia-is-critical-because-they-account-for-42-of-regions-gdp-report/),
  [bank statement fraud report](https://www.inscribe.ai/blog/why-bank-statement-fraud-is-the-1-document-concern-for-lenders-in-2026)
- PSAK renumbering: [IAI publication](https://web.iaiglobal.or.id/assets/files/file_publikasi/Perubahan_Penomoran_PSAK_ISAK_dalam_SAK_Indonesia.pdf)
- Payment diversion: [FBI IC3 2024 report figures via Nacha](https://www.nacha.org/news/fbis-ic3-finds-almost-85-billion-lost-business-email-compromise-last-three-years)
- Memory Bank and Sessions: [Memory Bank quickstart with ADK](https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/memory-bank/adk-quickstart)
- RAG Engine: [Understanding RagManagedDb](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/rag-engine/understanding-ragmanageddb),
  [RAG Engine billing](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/rag-engine/rag-engine-billing)
- Firestore: [vector search](https://docs.cloud.google.com/firestore/docs/vector-search)
- ADK traces: [Cloud Trace observability for ADK](https://adk.dev/integrations/cloud-trace/)
- DeepEval: [Vertex AI (Gemini) as the judge](https://www.deepeval.com/integrations/models/vertex-ai)
