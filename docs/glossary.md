# Glossary

| Term | Meaning in Kredibel |
|---|---|
| **Accounting framework** | IFRS or US GAAP, chosen per workspace; decides each category's cash-flow class and the wording of statement lines (`contracts/policy/categories.v1.yaml`) |
| **Adaptive reading** | The default reading design: one AI reading per page plus a deterministic witness; Document AI parsers only on escalation ([ADR-010](adr/ADR-010-adaptive-extraction-ai-reader-and-witness.md)) |
| **ADK** | Agent Development Kit: Google's open-source framework for agents and agent workflows (we use 2.x graph and dynamic workflows) |
| **Agent events** | One BigQuery row per model call, tool call, node output or error of a run, written by the ADK BigQuery Agent Analytics plugin ([ADR-017](adr/ADR-017-agent-observability-on-google-cloud.md)) |
| **Agent Platform** | Gemini Enterprise Agent Platform, the 2026 name of Vertex AI |
| **Agreement score** | Share of compared fields on which the AI reader and the witness (or, with escalation, any two sources) produced the same value |
| **AI reader** | Gemini reading one page **image** and returning every value as printed; it never sees the text layer |
| **Alias** | An accepted alternative spelling of the workspace's name (e.g. as printed on statements), used for matching |
| **Auto-match rate** | Share of a month's bank lines (not excluded) that were matched automatically |
| **Bank line** | One row of a bank statement: date, description, signed amount, printed balance |
| **Coming soon** | A plan, language or feature (e.g. the loan readiness report) that is visible in the UI but disabled; it cannot be selected or bought |
| **Consensus** | The merged reading of a value with its status: `AGREED`, `CONFLICT`, `SINGLE_SOURCE`, `MISSING` |
| **Content duplicate** | A different file with the same content (same statement period, invoice, receipt or ledger line); held until a person decides |
| **Corroboration rule** | A model's visual suspicion cannot exceed MEDIUM unless a deterministic check found a problem in the same place |
| **Counterparty** | A client, supplier, lender, owner, government body or other party the business's money flows to or from, derived from the books, with the bank accounts seen for it |
| **Coverage check** | The verifier step that turns printed amounts the AI reader missed into witness-only rows |
| **DeepEval** | Open-source evaluation library we use, with Gemini on Agent Platform as the judge, to measure the Finance Assistant |
| **Entitlement** | A plan limit or feature checked by the server before an action that costs money or a seat |
| **Escalation** | Re-reading a low-agreement page with a Document AI parser (Form Parser or Invoice Parser), within a monthly budget (P1) |
| **Evidence ref** | Pointer from a finding, fact, match or suggestion to a document, page and bounding box, or a record |
| **Exact duplicate** | A file with the same SHA-256 as one already uploaded; recorded, never read, never counted |
| **Extraction file** | A read page in Markdown: page type, reading method, witness text, line items and both readings of each value |
| **Fact** | A computed, citable number with an ID (`fact:2026-03:money_in`), value and inputs |
| **Finance Assistant** | The chat (P1) that answers questions about the books with read-only tools, retrieval and memory of preferences ([ADR-014](adr/ADR-014-finance-assistant-tools-rag-memory.md)) |
| **Finding** | Result of a check: code, severity, explanation, next steps, evidence |
| **Free trial** | The only available plan: 30 days with limits from `contracts/plans.v1.yaml`; afterwards new uploads stop, reading and fixing continue |
| **Generation** | A counter on each month, increased by every change to its data; only the month run of the latest generation writes |
| **Grounding guard** | Code that checks every number and citation in an explanation or assistant answer against facts and findings |
| **Held** | A possible duplicate's values, excluded from figures, matching and the money flow until a person decides |
| **IAS 7 / PSAK 207** | Statement of Cash Flows standard (operating / investing / financing); PSAK 207 is Indonesia's equivalent of IAS 7 |
| **Label** | One AI decision a person can check (document type, page type, category, counterparty role, a value), with its confidence and source; `AI_PROPOSED`, `VERIFIED` or `CORRECTED` ([ADR-016](adr/ADR-016-human-verified-labels-and-learning-loop.md)) |
| **Ledger export** | A general-ledger file (CSV or XLSX) from the business's accounting tool, one row per journal line |
| **Ledger mapping** | Which column of a ledger export is the date, account, description, reference, debit and credit; proposed by Gemini from the header and value shapes, confirmed once per layout by the user |
| **Market pack** | Extra rules and formats for a market's local-language bank statements (later) |
| **Match** | A link between bank lines and documents or ledger entries that explain them, with a method (`AUTO`, `MANUAL`), score and reasons |
| **Memory Bank** | Agent Platform's long-term memory for agents; Kredibel stores only user preferences there, per workspace and user |
| **Model Armor** | Google Cloud service that screens prompts, responses and files for prompt injection, jailbreaks, malicious URLs and sensitive data |
| **Money flow** | The Sankey of a period. Statement view (default): revenue by client and other money in → bank accounts → activity (operating, investing, financing, kept) → statement line. Counterparties view: sources → bank accounts → who was paid |
| **Month run** | One execution of `month_workflow` for one month: reconcile, check, score risk, explain, build flows, sync review items |
| **Next steps** | What to do about a finding, from a fixed catalog in `risk.v1.yaml`, ordered and phrased by the explainer |
| **Order independence** | The same documents give the same matches and results whatever order they were uploaded in |
| **Page triage** | Upload-time test per page: usable text layer, none or unusable (→ OCR witness), blank (→ not read) |
| **Page type** | What a page is (transactions, statement summary, invoice, receipt, ledger table, terms or cover, blank, other), returned by the page reader |
| **Payment diversion** | Fraud in which a supplier's bank account is changed so payments go to someone else; flagged by `X08` |
| **Plan** | A tier in `contracts/plans.v1.yaml` with status `AVAILABLE` (Free trial) or `COMING_SOON` (Starter, Professional, Enterprise) |
| **Profile suggestion** | A value Kredibel found in the documents for the workspace's profile (bank account, tax ID, address, alias, related party), with evidence; applied only when the user accepts it |
| **Provenance** | Where a value came from: document, page, bounding box, which source(s), raw strings |
| **Quarantine** | A document flagged by Model Armor; never sent to any model |
| **Reconciliation** | Matching a month's bank lines to invoices, receipts and ledger entries, and explaining the rest |
| **Related party** | A person or company connected to the business (owner, director, family); money from them is not sales (P1) |
| **Review item** | One exception for a person to resolve: unmatched line or document, proposed match, possible duplicate, uncertain value, ledger difference, type or mapping to confirm |
| **Revision** | An incremental save appended to a PDF; earlier revisions can be recovered |
| **Risk level** | `LOW`, `MEDIUM`, `HIGH` or `CRITICAL` for a document or a month, computed from its findings by `risk.v1.yaml` |
| **Run** | One execution of a workflow: a document run or a month run |
| **Run graph** | The nodes of a run drawn as a graph with status, duration, model and tokens, from the run's stages and ADK traces (P1) |
| **Sign-off** | A reviewer locking a reconciled month (P1) |
| **Statement line** | Where a category rolls up on the dashboard's cash-flow view (Revenue, Cost of sales, Operating expenses, Taxes paid, Finance costs, …), named in the workspace framework's wording; a cash-basis grouping, not an accrual income statement |
| **Tax ID** | Business taxpayer identification number printed on invoices |
| **Thorough mode** | `EXTRACTION_MODE=thorough`: a Document AI parser also reads every page (evals; a future paid tier) |
| **VAT** | Value-added tax on invoices (11% in the synthetic data) |
| **Verdict** | Per-document integrity outcome: `CLEAN`, `SUSPICIOUS`, `TAMPERED`, `UNVERIFIABLE` |
| **Verified by a person** | A label a person confirmed (`VERIFIED`) or corrected (`CORRECTED`); never overwritten by a model and the only kind used for evals and datasets |
| **Verifier** | Pure code that checks every AI-read value against the witness by position and assigns its status and box |
| **Withholding tax** | Tax a client deducts from a payment; explains invoices paid at ~98% of the total |
| **Witness** | The independent second reading of a page: the PDF text layer (free) or Document AI Enterprise OCR for scans and photos. It says what is printed where; it never interprets |
| **Witness-only row** | A row the witness shows but the AI reader missed; `SINGLE_SOURCE`, so it can never support a CRITICAL finding |
| **Workspace** | The business or person whose books are checked, as an account in Kredibel (an `org` in data and code), with members, a plan and settings |
