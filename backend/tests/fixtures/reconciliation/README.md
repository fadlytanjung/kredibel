# Reconciliation replay fixtures

Fictional S1, seed 1, March books from `tools/synthetic`. All PDFs retain the synthetic watermark.
Regenerate together with their source truth: `make reconciliation-fixtures`.

- `statement-2026-03.pdf`: full March bank statement.
- `inv-sales-2026-03-01.pdf`: Daybreak Café sales invoice, paid 21 March.
- `inv-purchase-2026-03-01.pdf`: Green Valley Farms purchase invoice.
- `receipt-2026-03-01.pdf`: Swift Courier card receipt, rendered as a text PDF from the same S1
  data (the standard S1 bundle renders it as a photo).
- `receipt-2026-03-02.pdf`: Cendana Fuel Station cash receipt.

The till rolls print no currency: the replay explicitly records a person's agreement to use their
unchanged amounts as IDR. No FX conversion. Real uploads must obtain that agreement from the user.
Recorded reader responses come from `truth.json`; local PDF rendering/grounding, checks,
categorization, assignment, API and month workflow run normally with in-memory repositories.

`make demo-reconciliation` checks both upload orders; `make trace-up` then
`make demo-reconciliation-traced` also exports the workflows to `http://localhost:16686`.
This small replay does not claim the full S1/S4/S5 acceptance gates or real Gemini accuracy.
