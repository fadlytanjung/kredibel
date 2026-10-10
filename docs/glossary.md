# Glossary

| Term | Meaning in Kredibel |
|---|---|
| **Adaptive reading** | The default extraction design: one AI reading per page plus a deterministic witness; Document AI parsers only on escalation ([ADR-010](adr/ADR-010-adaptive-extraction-ai-reader-and-witness.md)) |
| **ADB** | Average daily balance: mean of end-of-day balances over the days of a month |
| **ADK** | Agent Development Kit: Google's open-source framework for agents and agent workflows (we use 2.x graph/dynamic workflows) |
| **Agent Platform** | Gemini Enterprise Agent Platform, the 2026 name of Vertex AI |
| **Agreement score** | Share of compared fields on which the AI reader and the witness (or, with escalation, any two sources) produced the same value |
| **AI reader** | Gemini reading one page **image** and returning every value as printed; it never sees the text layer |
| **Alias** | An accepted alternative spelling of the applicant's name (e.g. as printed on statements), used for matching |
| **Applicant** | The individual or company applying for a loan; onboarded once and reused across cases (the "borrower" in lending terms) |
| **Beneficial owner** | A person who ultimately owns or controls a company applicant; recorded as a related party |
| **BPR** | Indonesian rural/community bank, a typical SME lender (proper name of the bank category) |
| **CADS** | Cash available for debt service = net operating cash flow − owner drawings |
| **Case** | One loan application of one applicant under assessment |
| **Coming soon** | A plan, language or feature that is visible in the UI but disabled; it cannot be selected or bought |
| **Consensus** | The merged extraction result with a status per value: `AGREED`, `CONFLICT`, `SINGLE_SOURCE`, `MISSING` |
| **Corroboration rule** | A model's visual suspicion cannot exceed MEDIUM unless a deterministic check found a problem in the same place |
| **Counterparty** | A party the applicant's money flows to or from (client, supplier, lender, own account, related party, government, other), derived per run |
| **Coverage check** | The verifier step that turns printed amounts the AI reader missed into witness-only rows |
| **DSCR proxy** | CADS ÷ (existing debt service + proposed installment), computed from bank-statement data |
| **Entitlement** | A plan limit or feature checked by the server before an action that costs money or a seat |
| **Escalation** | Re-reading a low-agreement page with a Document AI parser (Form Parser or Invoice Parser), within a per-case budget (P1) |
| **Evidence ref** | Pointer from a finding/fact/suggestion to a document, page and bounding box, transaction, invoice or fact |
| **Fact** | A computed, citable number with an ID (`fact:dscr_proxy`), value, unit and inputs |
| **Finding** | Result of a check: code, severity, explanation, evidence |
| **Free trial** | The only available plan: 30 days with limits from `contracts/plans.v1.yaml`; afterwards AI actions stop, reading and deciding continue |
| **Grounding guard** | Code that verifies every number and citation in the memo against facts |
| **Hard stop** | Policy rule that overrides the grade's recommendation (e.g. `TAMPERED_DOCUMENT` → DECLINE) |
| **IAS 7 / PSAK 207** | Statement of Cash Flows standard (operating / investing / financing); PSAK 207 is Indonesia's equivalent of IAS 7 |
| **Market pack** | Extra rules and formats for a market's local-language bank statements (P2) |
| **Model Armor** | Google Cloud service that screens prompts, responses and files for prompt injection, jailbreaks, malicious URLs and sensitive data |
| **NOCF** | Net operating cash flow = operating inflows − operating outflows |
| **OJK** | Indonesia's Financial Services Authority (proper name of the regulator) |
| **Page triage** | Upload-time test per page: usable text layer, none or unusable (→ OCR witness), blank (→ not read) |
| **P2P lending** | Online peer-to-peer lending platforms; repayments to them are tagged `P2P_LENDING` |
| **Plan** | A tier in `contracts/plans.v1.yaml` with status `AVAILABLE` (Free trial) or `COMING_SOON` (Starter, Professional, Enterprise) |
| **Profile suggestion** | A value Kredibel found in the documents for the applicant's profile (account, tax ID, address, alias, related party, key client/supplier), with evidence; applied only when an analyst accepts it |
| **Provenance** | Where a value came from: document, page, bounding box, which source(s), raw strings |
| **Quarantine** | A document flagged by Model Armor; never sent to any model |
| **Related party** | A person or company connected to the applicant (beneficial owner, director, shareholder, guarantor, signatory); money from them is not sales |
| **Revision** | An incremental save appended to a PDF; earlier revisions can be recovered |
| **Run** | One execution of the analysis pipeline for a case |
| **Spreading** | Manually transcribing statement data into a spreadsheet for analysis |
| **Tax ID** | Business taxpayer identification number printed on invoices |
| **Thorough mode** | `EXTRACTION_MODE=thorough`: a Document AI parser also reads every page (evals; a future paid tier) |
| **VAT** | Value-added tax on invoices (11% in the synthetic data) |
| **Verdict** | Per-document integrity outcome: `CLEAN`, `SUSPICIOUS`, `TAMPERED`, `UNVERIFIABLE` |
| **Verifier** | Pure code that checks every AI-read value against the witness by position and assigns its status and box |
| **Withholding tax** | Tax a customer deducts from a payment; explains invoices paid at ~98% of the total |
| **Witness** | The independent second reading of a page: the PDF text layer (free) or Document AI Enterprise OCR for scans. It says what is printed where; it never interprets |
| **Witness-only row** | A row the witness shows but the AI reader missed; `SINGLE_SOURCE`, so it can never support a CRITICAL finding |
| **Workspace** | A lender's account in Kredibel (an `org` in data and code), with members, a plan and settings |
