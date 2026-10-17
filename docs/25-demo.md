# 25. Try Kredibel with the demo account

_Spec 024. Every document in the demo is **synthetic**: the business, the bank, the people and the
numbers are invented, and every page is watermarked "SYNTHETIC — FOR TESTING"._

## Sign in

| | |
|---|---|
| Where | <https://kredibel-app.web.app/login> (or <https://kredibel.app/login>) |
| Email | `demo@kredibel.app` |
| Password | `Kredibel-Demo-2026` |

Write the email and password in the form below **Sign in with Google** and press **Sign in** (no
Google account needed). Anyone can use this account at the same time, so what you change, someone
else may see; reset it whenever you like (below). **Do not upload real documents to it**: everyone
who signs in sees them. To try your own books, sign in with Google instead and create your own
workspace.

## What is in it

Sunrise Coffee Roasters, a coffee roaster in Bandung, **August to October 2026**, at about a hundred
documents a month: three bank statements of Archipelago Commerce Bank (about a hundred lines each),
117 sales invoices to 14 clients, 77 purchase invoices from 9 suppliers (one of them a scanned copy),
102 receipts (half photos, half PDFs) and the general-ledger export: 300 files, read by Kredibel and
reconciled month by month. A bank line is matched to its invoice or receipt, or else to its booking
on the ledger's bank account (1110, mapped in Settings › Bank accounts), so at least 85% of bank
lines are matched automatically each month; what is left is in the Review queue.

Planted on purpose, to see what Kredibel finds:

| Month | What happened | Where to look |
|---|---|---|
| August | A credit on the statement was edited in a PDF editor (another font, a second revision) | Risk: August is **CRITICAL**; the document's findings show the edited amount on the page |
| August | A purchase invoice was scanned and uploaded again | Review: a possible copy held, not counted twice |
| September | Two supplier invoices from Bluewater were never paid | Review and Risk: unpaid invoices from an unknown party |
| October | Roastline's invoice asks for payment to a new bank account, and it was paid there | Risk: October is **HIGH** (a supplier paid to an account never seen before) |

Then try: the **Dashboard** (money in and out, the money flow and the profit and loss), a **month**
(its matches, with the reason for each), **Transactions** (every bank line with its IFRS and US GAAP
class, subledger and what it is matched to), the **Review** queue, **Labels** (what the AI read, to confirm
or correct), **Runs** (every workflow, its model calls and cost), and the **Assistant** ("How much
money went out in October?").

## Reset the demo

- In the app's API: `POST /api/workspaces/demo/reset` while signed in as the demo account (any other
  account gets 403; it takes about 20 seconds); sign out and in again afterwards. The fresh copy has
  no goal yet, so the first page asks what you want first: keep the books, or write the money in and
  out you expect per month to compare with what Kredibel finds.
- From the repository: `make demo-account DEMO_ACCOUNT_EMAIL=demo@kredibel.app DEMO_ACCOUNT_PASSWORD=…`
  creates the account if needed, sets its password and replaces its workspace with a fresh copy of the
  demo company. It takes a few seconds: the copy is made from the demo company, nothing is read again.

## Rebuild the demo company itself

`make demo-template` generates the books (`kredibel-synth demo --shift-months 5 --window 2026-08:2026-10
--pack --per-month 100`) and uploads the pack through the normal reading and reconciliation, ten
documents at a time (about 45 minutes for 300; it calls Gemini and Document AI). Wipe the demo company
(`DEMO_TEMPLATE_ORG`) first with `uv run python -m scripts.clean_workspace --org org_demo_template
--reset-usage`: the template is on the free trial, and without `--reset-usage` a second rebuild in the
same month stops at the trial's monthly limit. Every new demo company and the demo account copy it; a
copy takes the records and the files, not the reading cache, so it stays within a request's time.

The pack is also a folder of files you can upload yourself into any workspace:
`tools/synthetic/out/demo-aug-oct/pack/` (in `upload-order.txt` order; then map the bank account to
ledger account 1110 in Settings › Bank accounts).
