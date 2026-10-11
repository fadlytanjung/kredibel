# Kredibel — Proposal (working draft)

> Working copy for the Hack2skill submission. Replace every `⟨…⟩` before submitting. Quote only
> numbers from the latest eval report or from the cited sources. Check the portal's character limits.

**Theme:** 1 — BFSI: Intelligent Risk, Fraud & Financial Experiences
**Team:** ⟨names⟩ · **Prototype:** ⟨URL⟩ · **Video:** ⟨URL⟩ · **Repository:** ⟨URL⟩

---

## 1. Problem

Small businesses are the backbone of Southeast Asian economies, and most of them close their books by
hand. Invoices, supplier bills and receipts arrive all month; the bank statement arrives at month end;
someone matches them in a spreadsheet. Three things go wrong:

- **Duplicates:** the same statement uploaded twice, a supplier invoice scanned again, a receipt
  photographed by two people. Expenses get counted twice; suppliers get paid twice.
- **Edited documents:** editing a PDF takes minutes. In a 2026 industry survey, 85.6% of fraud and
  risk leaders named bank statements the document most vulnerable to manipulation, and the same vendor
  reports roughly 6% of documents in its network flagged as manipulated in 2025 (Inscribe,
  vendor-reported).
- **Silent mismatches:** an invoice paid to a bank account the supplier never used before. Business
  email compromise, which often works exactly this way, cost US businesses close to USD 2.8 billion in
  2024 according to the FBI's IC3.

## 2. Solution

**Kredibel** is an AI finance workspace that checks your books. A business (or its accountant)
uploads statements, invoices, receipts and the general-ledger export **in any order**. Kredibel:

1. **Catches duplicates before they count.** Exact copies are recorded and never read; a re-exported
   statement, a re-scanned invoice or a re-photographed receipt is held until a person decides.
2. **Reads every number twice, for the price of once.** Gemini reads every page image; the PDF's own
   text layer (or Document AI OCR for scans and photos) is an independent witness. A value both agree
   on is trusted; disagreement is uncertainty, never an accusation.
3. **Imports ledger files safely.** Gemini proposes the column mapping from the header and value
   shapes only; the user confirms it once; code imports every row.
4. **Reconciles every month automatically, in any upload order.** Bank lines are matched to invoices,
   receipts and ledger entries with reasons; only unique, high-scoring matches are automatic; a month
   is recomputed whenever its data changes and gives the same result whatever the order.
5. **Keeps people in charge of the exceptions.** The 15–20% AI cannot match goes to a review queue
   with evidence and the right fixes; every fix is audited and re-reconciles the month.
6. **Explains fraud risk.** Running balances, PDF revisions, font anomalies, statement continuity and
   payments to a supplier's new account produce findings with evidence; a policy file sets each
   month's risk level; Gemini explains it and orders the next steps, and a grounding guard checks every
   number it writes.
7. **Shows where the money went** on a dashboard with a money-flow Sankey; a Finance Assistant (P1)
   answers questions with read-only tools, retrieval and memory of the user's preferences.

## 3. How it works (Google Cloud)

- Two **ADK 2.x workflows** on **Cloud Run**, fed by **Cloud Tasks**: a dynamic `document_workflow`
  (classify, read pages in parallel, verify, import ledgers, check, detect duplicates, categorize) and
  a static `month_workflow` (reconcile, check, score risk, explain, build the money flow, sync review
  items), with generations so only the latest month run writes. ADK traces go to **Cloud Trace** and
  drive a run graph in the app.
- **Gemini** (Flash, Flash-Lite on Gemini Enterprise Agent Platform) for reading page images,
  classification, ledger mapping, categorization and explanations, always with structured outputs.
- **Document AI** Enterprise OCR as the witness for scans and receipt photos; the PDF text layer is the
  witness for digital pages.
- **Firestore** (system of record, realtime progress, vector search for the assistant) and **Cloud
  Storage**; **Firebase Auth**; **Model Armor** for files that try to instruct the AI.
- **Agent Platform Sessions and Memory Bank** give the Finance Assistant conversation state and
  per-user preferences; DeepEval with a Gemini judge measures its answers.
- A self-serve **workspace** for an individual or a company with a **30-day free trial**; paid tiers
  and a loan readiness report shown as coming soon; limits enforced server-side.

## 4. Impact

- **Business owners:** a month closed in an hour instead of days; duplicates and edited documents
  caught before they reach the books.
- **Accountants:** one queue of exceptions across clients' documents, each with evidence; fixes that
  survive re-runs.
- **Fraud prevention:** payment diversion and doctored statements flagged with the page and the
  reason, not a black-box score.

Measured on our synthetic scenarios (⟨date⟩, ⟨n⟩ runs): ⟨bank lines matched automatically⟩,
⟨wrong automatic matches⟩, ⟨duplicates caught⟩, ⟨seeded tampering detected⟩, ⟨cost per page⟩.

## 5. Feasibility

Working prototype on Cloud Run, built in ⟨n⟩ days by a team of ⟨n⟩ with spec-driven development.
A synthetic data generator writes half-years of books with ground truth for six scenarios (a clean
half-year, an edited statement, duplicates, payment diversion, reverse upload order, prompt
injection). All components are managed Google Cloud services; no custom model training is required.

## 6. Scalability & path to production

- Serverless throughout; per-page parallelism with concurrency caps; months recomputed incrementally.
- **Data residency path:** in-region OCR and model endpoints, VPC Service Controls (ADR-009).
- **Market expansion** is configuration: checks, matching thresholds, categorization rules and risk
  levels are versioned policy files.
- **Next:** team roles and month sign-off, bank feeds, e-invoice validation, accounting-tool
  connectors, and a **loan readiness report** built from verified months.

## 7. Responsible AI

People resolve the exceptions; every match, finding and number shows its source; possible duplicates
are held, never deleted; "unverifiable" is an honest outcome instead of a guess; no personal attributes
are used; synthetic data only in this prototype.

---

Sources: bank statement fraud statistics ([Inscribe, 2026](https://www.inscribe.ai/blog/why-bank-statement-fraud-is-the-1-document-concern-for-lenders-in-2026));
business email compromise losses ([FBI IC3 2024 report via Nacha](https://www.nacha.org/news/fbis-ic3-finds-almost-85-billion-lost-business-email-compromise-last-three-years)).
