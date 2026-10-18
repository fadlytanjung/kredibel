# Pitch deck content

> Content for the challenge's **prescribed pitch-deck template**: copy each section into the matching
> slide of the template (keep its layout, fonts and order; do not add slides it does not have). The
> pictures named here exist in the repository. Numbers are from the demo company (synthetic,
> August–October 2026) on production, 17 Oct 2026, and from the cited source.
>
> The finished deck is [`kredibel-pitch-deck.pptx`](kredibel-pitch-deck.pptx) (PDF:
> [`kredibel-pitch-deck.pdf`](kredibel-pitch-deck.pdf)); this file is the content it was built from.

## 1. Team

⟨Team name, members and roles, as on the registration.⟩

## 2. The idea in brief

**Kredibel checks a small business's own books.** Upload bank statements, invoices, receipts and the
ledger export in any order; Kredibel reads every page twice, reconciles every month, flags what looks
wrong and shows the evidence behind every number. *Every number has a source.*

## 3. The problem

- A small business closes its books by hand: statements at month end, invoices and receipts all
  month, a ledger from the bookkeeper. Matching them takes days.
- What slips through: the same invoice counted twice, an edited PDF statement, a supplier's "new bank
  account" that belongs to someone else, a payment nobody booked.
- Organizations lose an estimated **5% of revenue to fraud** each year; for businesses with fewer than
  100 employees the **median loss is USD 141,000** per case (ACFE, *Occupational Fraud 2024: A Report
  to the Nations*).

## 4. The solution and what makes it different

- **Grounded reading:** Gemini reads each page from its image and numbered text chunks and cites where
  every value is printed; code, not the model, checks it. Scans and photos get a second reader
  (Document AI OCR).
- **Numbers come from code:** matches, totals and risk levels are deterministic and explained; the
  same data gives the same result in any upload order.
- **Reconciliation that finishes:** bank lines are matched to invoices, receipts and, where no
  document exists, to their booking in the ledger: 95% automatically on the demo company.
- **Forensics:** duplicates held, edited PDFs (fonts, revisions, running balances), payments to a
  changed supplier account, unpaid invoices from unknown suppliers.
- **People decide the rest:** one short review queue; every AI decision is a label a person can
  confirm or correct; every workflow run is traced with its model calls and cost.

## 5. Features

Dashboard (money in and out, money flow, profit and loss, cash-flow statement), expectations against
the reconciled months, Transactions (every bank line with its IFRS and US GAAP class, subledger and
match), month reconciliation with reasons, risk levels with an evidence viewer, review queue,
documents with exact and possible copies, labels, runs, finance assistant with citations, a public
demo account and a guided tour.

## 6. Process flow

Upload → exact copy? (recorded, not read) → classify → read every page (Gemini + text layer / OCR)
→ verify every value → copies and tampering checks → categorize → month run: reconcile (documents,
then the ledger) → risks with evidence → review queue → dashboard, transactions, assistant.
Picture: [`docs/diagrams/analysis-swimlane.drawio.svg`](../diagrams/analysis-swimlane.drawio.svg).

## 7. Architecture

Firebase Hosting and Authentication in front; Cloud Run `kredibel-web` (API) and `kredibel-worker`
(ADK workflows) behind Cloud Tasks; Firestore for the books, live updates and vector search; Cloud
Storage for files; Gemini and Document AI for reading; Cloud Trace for every run.
Picture: [`docs/diagrams/gcp-architecture.drawio.svg`](../diagrams/gcp-architecture.drawio.svg).

## 8. Technologies

Google Cloud: Firebase Hosting, Firebase Authentication, Cloud Run, Firestore (incl. vector search),
Cloud Tasks, Cloud Storage, Gemini (Flash, Flash-Lite, embeddings) on Vertex AI, Document AI OCR,
Agent Development Kit, Cloud Trace, Secret Manager, Cloud Build. App: Python (FastAPI, Pydantic),
React, TypeScript, Vite.

## 9. Snapshots of the prototype

From the demo video (`docs/submission/demo-video/kredibel-demo.mp4`) or the app: the dashboard with
"What you expected", Transactions with a cash deposit's drawer, October's matches with reasons, the
edited statement in the evidence viewer, the review queue, a run's waterfall, the assistant's cited
answer.

## 10. Results and cost

- Demo company: 300 files (about 100 a month), 95% of bank lines matched automatically (95.2%,
  92.2%, 98.0%), Critical and
  High months found with evidence, a held copy, an exact copy never read.
- Test scenario S1: 84 of 87 bank lines without a document matched to their ledger booking, none
  wrongly.
- Reading cost measured on an earlier, 80-document demo company: about USD 0.43 (89 pages).

## 11. What comes next

Loan-readiness report for lenders, Model Armor screening of uploads, team invites, the assistant's
memory, more banks and local formats, a measured evaluation suite on real documents (with consent).

## 12. Links

- Prototype: <https://kredibel.app> (mirror <https://kredibel-app.web.app>; demo sign-in: `demo@kredibel.app` /
  `Kredibel-Demo-2026`; [docs/25](../25-demo.md))
- Video: https://youtu.be/5UI2NZFmzrk
- Repository: <https://github.com/fadlytanjung/kredibel>
