# Walkthrough for judges

What to click in the deployed prototype, in about ten minutes, and what you should see. Everything in
the demo account is **synthetic** (Sunrise Coffee Roasters, August–October 2026); the video follows
the same path ([`demo-video/script.md`](demo-video/script.md)).

## Sign in

1. Open <https://kredibel-app.web.app/login>.
2. Under **Sign in with Google**, enter `demo@kredibel.app` and `Kredibel-Demo-2026`, then **Sign in**.
3. If the account was just reset you are asked **What would you like Kredibel to do first?** Choose
   **Check what I expect** and write, for example, September: 820000000 in, 840000000 out; October:
   1000000000 in, 620000000 out; then **Save and go to my dashboard**. (Or **Keep my books**.)

The account is shared: someone may have changed it. To start from a fresh copy, see
[docs/25](../25-demo.md#reset-the-demo).

## What to look at

| Where | What you should see | What it shows |
|---|---|---|
| **Dashboard** | August–October: money in and out, **Matched by Kredibel 95.2%**, *To review 20*; **What you expected** (if you wrote expectations): September as expected, October's money out 85,933,026 more | Figures come from code; expectations are compared, never judged |
| **Transactions** | Every October bank line, ten a page: category and who chose it, IFRS and US GAAP class, subledger, reading, what it is matched to. Open a **CASH DEPOSIT**: *Sales receipts (From its match)*, matched to a ledger entry | A line the words cannot categorize takes the category of its booking |
| **Reconciliation › October** | "High risk this month" with citations and next steps; each bank line *Matched by Kredibel* with its reason (*Same amount, Same party, Booked once in your ledger's bank account*) | Deterministic matching with reasons, documents first, then the ledger |
| **Risk** | August **Critical**: A01 (the balance on 14 Aug does not follow), A02, M01–M04 (edited in a PDF editor, another font in one amount); open **M04** to see the amount lit on the page. October **High**: X08, a supplier paid into a new bank account. September **Medium**: two unpaid invoices from an unknown supplier | Forensics on grounded values, each with evidence |
| **Documents** | 300 files read (about 100 a month); upload `statement-2026-10.pdf` again (from `tools/synthetic/out/demo-aug-oct/pack/` after `make synth`, or any file already there): *Already uploaded… Not read again and not counted.* The scanned copy of an August invoice is held as a possible copy | Copies are never read or counted twice |
| **Review** | Twenty decisions: the scanned copy (side by side with the original), payments to confirm, the edited 7,250,000 credit with no document, two unpaid invoices, values to check, the ledger file's type | People decide what code cannot |
| **Labels** | Every AI decision (document and page types, categories, values) with its confidence, to confirm or correct | The AI suggests; people decide |
| **Runs** | Each document and month workflow; open a document run: its nodes, each Gemini call with its prompt version, tokens and cost | Every run traced (ADK, Cloud Trace) |
| **Assistant** | Ask "How much money went out in October 2026?": *IDR 705,933,026.00* with a citation to the month's figure | Answers from the books, cited, checked |
| **Settings › Profile** | *What you want first*, with a link to change it; IFRS or US GAAP | |

## If something looks wrong

- Your own files: sign in with Google instead and create a workspace (free trial); do not upload real
  documents to the shared demo account.
- The first page after a quiet period can take a few seconds (Cloud Run starting).
