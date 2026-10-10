# Kredibel — Proposal (working draft)

> Working copy for the Hack2skill submission. Replace every `⟨…⟩` before submitting. Quote only
> numbers from the latest eval report or from the cited sources. Check the portal's character limits.

**Theme:** 1 — BFSI: Intelligent Risk, Fraud & Financial Experiences
**Team:** ⟨names⟩ · **Prototype:** ⟨URL⟩ · **Video:** ⟨URL⟩ · **Repository:** ⟨URL⟩

---

## 1. Problem

Small and medium businesses are the backbone of Southeast Asian economies, yet they remain chronically
under-financed; a frequently cited estimate puts the region's SME funding gap at about
USD 300 billion. Lenders that serve them (bank SME units, rural banks, multifinance companies and P2P
platforms) underwrite mostly from documents the borrower supplies: bank statements and invoices.

That creates three problems:

- **Slow:** analysts re-type months of transactions before analysis can start.
- **Easy to fool:** editing a PDF or buying a statement template is cheap. In a 2026 industry survey,
  85.6% of fraud and risk leaders named bank statements the document type most vulnerable to
  manipulation, and the same vendor reports roughly 6% of documents in its network flagged as
  manipulated in 2025 (Inscribe, vendor-reported).
- **Hard to audit:** memo numbers can't be traced back to their source.

## 2. Solution

**Kredibel** is an agentic credit analyst. A lender uploads a borrower's statements and invoices;
Kredibel returns a verified, evidence-linked cash-flow assessment and a draft credit memo in minutes.
It flags tampered documents and unsupported revenue, and leaves the decision to a human analyst.

What makes it different:

1. **Two readings before an accusation, for the price of one.** Gemini reads every page image; the
   PDF's own text layer (or Document AI OCR for scans) is an independent witness. Values both agree on
   become trusted; disagreement is reported as uncertainty, never as fraud. About USD 0.34 per case.
2. **Forensics, not just OCR.** Running-balance and total arithmetic, PDF revision history (including
   recovering the original value from an edited file), font anomalies in amount columns, month-to-month
   continuity, account-holder checks.
3. **Follow the money.** IAS 7 cash-flow classification, average daily balance, debt-service coverage,
   and invoice-to-bank reconciliation that exposes revenue that never arrived.
4. **Every number has a source.** Findings and memo figures link to the exact page region; a
   grounding guard verifies every number Gemini writes against computed facts.
5. **Onboarding that fills itself in.** Applicants are onboarded as individuals or companies; Kredibel
   suggests their accounts, tax ID, address, clients and partners from the documents, each with the
   page it came from, for the analyst to accept.
6. **Safe by design.** Documents are screened by Model Armor before any model reads them; models
   cannot change scores or decisions; tools are read-only; every decision is audited.

## 3. How it works (Google Cloud)

- **ADK 2.x workflow** on **Cloud Run** orchestrates screening → inspection → classification → page
  reading and verification (parallel) → forensics (parallel) → categorization → metrics → reconciliation →
  scoring → memo → verification, triggered through **Cloud Tasks**.
- **Gemini** (Flash, Flash-Lite, Pro on Gemini Enterprise Agent Platform) for classification,
  extraction, categorization, visual second opinion, explanations and the memo, always with
  structured outputs.
- **Document AI** Enterprise OCR as the independent witness for scanned pages (the PDF text layer is
  the witness for digital ones); Form and Invoice parsers on demand for doubtful pages.
- A lender **workspace** with self-serve onboarding and a **30-day free trial**; paid tiers shown as
  coming soon; limits enforced server-side.
- **Model Armor** screens uploaded files for prompt injection.
- **Firestore** and **Cloud Storage** hold cases and evidence; **Firebase Auth** secures access;
  **Agent Platform Sessions** give the case assistant memory.
- A transparent, versioned **policy scorecard** computes grades, hard stops and recommendations in code.

## 4. Impact

- **Analysts:** from days of spreading to minutes of review, starting from evidence instead of data
  entry.
- **Lenders:** fewer approvals on manipulated documents; consistent, defensible decisions; a complete
  audit trail.
- **SMEs:** faster answers and precise information requests instead of vague follow-ups. Honest
  borrowers aren't penalized by OCR errors, because uncertainty is never treated as fraud.

Measured on our synthetic scenarios (⟨date⟩, ⟨n⟩ cases): ⟨seeded tampering detected⟩,
⟨false tampered verdicts⟩, ⟨median time per case⟩, ⟨memo figures verified⟩.

## 5. Feasibility

Working prototype on Cloud Run, built in ⟨n⟩ days by a team of ⟨n⟩ with spec-driven development.
Synthetic data generator with ground truth for six scenarios (healthy, edited statement, fake
revenue, stressed borrower, perfect-looking fake, prompt injection). All components are managed
Google Cloud services; no custom model training is required.

## 6. Scalability & path to production

- Serverless throughout (Cloud Run, Cloud Tasks, Firestore, Document AI, Gemini); per-document
  parallelism with concurrency caps.
- **Data residency path:** in-region OCR and parsers where offered, in-region model
  endpoints, VPC Service Controls (documented in ADR-009).
- **Market expansion** is configuration: scorecard, categorization rules and tax rates are versioned
  policy files.
- Next: borrower upload portal, receipts and tax invoices, cross-lender duplicate-invoice registry,
  BigQuery portfolio analytics, calibration of the scorecard on a lender's outcomes.

## 7. Responsible AI

Human decides; explanations for every score component and finding; no protected attributes in
scoring; an explicit "unverifiable" outcome instead of guesses; synthetic data only in this prototype.

---

Sources: SME funding gap ([Crowdfund Insider, 2020](https://www.crowdfundinsider.com/2020/07/164576-300-billion-funding-gap-for-smes-in-southeast-asia-is-critical-because-they-account-for-42-of-regions-gdp-report/));
bank statement fraud statistics ([Inscribe, 2026](https://www.inscribe.ai/blog/why-bank-statement-fraud-is-the-1-document-concern-for-lenders-in-2026)).
