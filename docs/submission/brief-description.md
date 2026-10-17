# Brief description

> For the submission form's "Brief description" field. The short version fits a ~1,000-character
> limit; the long version adds the Google Cloud detail. Numbers come from the demo company
> (synthetic, August–October 2026) on production, 17 Oct 2026.

## Short version

Kredibel is an AI finance workspace that checks a small business's own books. You upload bank
statements, sales and purchase invoices, receipts and the general-ledger export, in any order.
Gemini reads every page from its image and its own text, and code checks that every value is printed
where Gemini says it is. Kredibel then holds copies so nothing is counted twice, finds edited PDFs and
payments to a supplier's new bank account, and reconciles each month: on the demo company 97% of bank
lines are matched automatically, to an invoice, a receipt or the ledger, each with its reason. What
it cannot decide goes to one short review queue; every month gets a risk level with the evidence;
and a finance assistant answers from the books' own figures with citations. Built on Firebase,
Firestore, Cloud Run and Gemini.

## How Kredibel uses Google Cloud

- **Firebase:** Firebase Hosting serves the React app and sends `/api/**` to Cloud Run. Firebase
  Authentication signs people in with Google, or with email and password for the public demo account;
  each person's workspace and role travel as custom claims that the API and the security rules check.
- **Firestore:** the books themselves: workspaces, documents and their pages, bank lines, invoices,
  receipts, ledger entries, matches, months, findings, review items, labels, runs and an audit trail.
  The browser listens to documents and months, so reading and reconciling progress shows live. Firestore
  vector search finds the passages the finance assistant cites. Every record carries a schema version.
- **Cloud Run:** two services. `kredibel-web` serves the API (and the app as a fallback);
  `kredibel-worker` (IAM only) runs the Agent Development Kit workflows: one per document (classify,
  read every page, verify the values, check duplicates and tampering, categorize) and one per month
  (reconcile, find risks, explain them). Cloud Tasks queues each document and each month; a Cloud Run
  job runs data migrations.
- **Gemini** (on Vertex AI, models as configuration): Gemini Flash reads statement, invoice and receipt
  pages from the page image plus numbered layout chunks and cites the chunk of every value (code, not
  the model, checks it); Gemini Flash-Lite classifies documents and categorizes bank lines; Gemini
  explains each month's risk with citations that a grounding guard checks, ranks the candidates of an
  ambiguous match, maps a new ledger layout's columns, and powers the finance assistant; Gemini
  embeddings index the passages it searches.
- **Also:** Document AI OCR as a second reader for scans and photos, Cloud Storage for files, Cloud
  Trace for every workflow run, Secret Manager for configuration, Cloud Build for delivery.

## What the demo shows (synthetic data)

- 39 files of Sunrise Coffee Roasters, August–October 2026: 97% of bank lines matched automatically
  (91.7%, 100%, 100% by month), each match with its reason.
- August is **Critical**: one statement was edited in a PDF editor (another font in one amount, a
  second revision, a running balance that no longer adds up).
- October is **High**: a supplier's invoice asked to be paid into a new bank account, and it was.
- A scanned copy of an invoice is held, never counted twice; an upload of a file already there is
  recorded and never read again.
- Expectations: the owner writes the money in and out they expect per month; the dashboard compares
  them with the reconciled months.
