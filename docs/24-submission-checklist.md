# Submission checklist

_Last checked: 17 Oct 2026. Live: `kredibel-web` and Firebase Hosting at the latest `main`. This page
is the single list to walk before the submission and before sharing the link; it points at the specs
and [`20`](20-implementation-status.md) for detail and never replaces them._

## 1. The live product

| Check | State | How to verify |
|---|---|---|
| `https://kredibel-app.web.app` serves the app and `/api/health` | Works | `curl -s https://kredibel-app.web.app/api/health` |
| `https://kredibel.app` serves the app | Works since the CDN cache was cleared (16 Oct) | open it in a browser, not only with `curl` (§4) |
| Sign-in on `https://kredibel.app` | **Works** (checked 17 Oct 2026: page, API, email and Google sign-in) | — |
| `https://www.kredibel.app` | **Not set up** (no DNS record, no certificate); hand out `kredibel.app` only | §4 |
| A new account can open the demo company and the guided tour starts by itself | Works (spec 021) | sign in with a fresh Google account → *Explore a demo company* |
| The public demo account signs in without Google and can be reset | Works (spec 024) | `demo@kredibel.app` on `/login` ([docs/25](25-demo.md)); `make demo-account` resets it |
| New workspaces | `MAX_WORKSPACES=200`, `SIGNUP_MODE` open | `infra/env-secret.sh keys`; counter in `system/signup` |
| Every gate green on `main` | `make check` | CI and local |

## 2. SDD status by spec

Open tasks are counted from each `tasks.md`; the status column is [`20`](20-implementation-status.md).

| Spec | Priority | Tasks done / open | State | What is open |
|---|---|---|---|---|
| 001 Foundation | P0 | 33 / 0 | Deployed | — |
| 002 Synthetic data | P0 / P1 | 16 / 1 | Built | T002-15 hidden white text (S6, P1) |
| 003 Document intake | P0 | 12 / 0 | Deployed | — |
| 004 Workflows | P0 | 12 / 0 | Deployed | — |
| 005 Reading | P0 / P1 | 10 / 3 | Deployed | T005-05 spike notes, T005-10 recorded S1 scenario, T005-12 escalation (P1) |
| 006 Duplicates and forensics | P0 | 12 / 0 | Deployed | — |
| 007 Reconciliation | P0 | 22 / 0 | Deployed | — |
| 008 Risk and explanations | P0 | 10 / 0 | Deployed | — |
| 009 Review queue | P0 | 10 / 0 | Deployed | — |
| 010 Dashboard and money flow | P0 | 9 / 2 | Deployed | T010-06 Lighthouse run, T010-08 status doc |
| 011 Finance Assistant | P1 | 2 / 7 | Partly built | the agent with tools, sessions and Memory Bank; DeepEval. Built: grounded answers over the books and quoted document passages (spec 022) |
| 012 Evals | P0 suites | 0 / 6 | **Not built** | runner, truth mapping, suites, report, README Results |
| 013 Workspace and plans | P0 / P1 | 19 / 3 | Deployed | T013-16/17 roles, members and invites (P1); T013-18 check on the deployed env |
| 014 Profile and counterparties | P0 / P1 | 5 / 2 | Deployed | aliases and related parties (P1) |
| 015 Trust extensions | P1 | 0 / 8 | Not built | Model Armor screening, sign-off, visual examiner, revision diff, CSV export, split |
| 016 Labels and learning | P1 | 9 / 2 | Deployed | E-LBL suite run, dataset export (later) |
| 017 Agent observability | P0 / P1 | 7 / 2 | Deployed | BigQuery plugin attach, Looker Studio report |
| 018 Classifications and P&L | P1 | 10 / 0 | Deployed | — |
| 019 UI parity | P0 | 5 / 0 | Deployed | — |
| 020 Public site | P0 | 30 / 2 | Deployed | T020-17 docs, T020-30 tests |
| 021 Demo and guided tour | P0 | 6 / 0 | Deployed | — |
| 022 Extraction store | P0 / P1 | 9 / 0 | Deployed | — |
| 024 Demo account, expectations, transactions | P0 / P1 | 7 / 0 | Deployed | — |

**The one P0 gap is spec 012**: there are no measured results yet, so neither the public site nor the
README may quote an accuracy, match rate or review share (§3).

## 3. Public copy against what is built

Audited 16 Oct 2026, every string of `frontend/src/shared/i18n/locales/en/public.json` and the plan
highlights of `contracts/plans.v1.yaml`. A claim stays only when it is built and deployed; a number
stays only when it was measured.

| Claim (before) | Finding | Now |
|---|---|---|
| "Files are screened before any model reads them"; "quarantined files never reach a model" | Model Armor screening is spec 015 (not built); nothing sets `QUARANTINED` | Prompts treat documents as data; the assistant's tools are read-only and workspace-scoped; screening "on the roadmap" |
| "A workspace can be deleted" (Security, FAQ, Privacy, landing) | Only a document can be deleted (`DELETE /api/documents/{docId}`) | Document deletion; a whole workspace "on request by email" |
| "Up to 3 team members", "up to three people" | The plan has 3 seats but invites are T013-17 (not built) | "Team invites coming soon" (site, plan contract, Plan & usage mock) |
| "More than nine in ten bank lines are matched automatically with no wrong automatic matches" | Never measured by the eval suite (spec 012). The August–October demo company (synthetic) has 71 of 73 bank lines matched automatically (17 Oct 2026, after bank-to-ledger matching); on S1 no automatic bank-to-ledger match is wrong (test) | How matching decides, no number |
| "About 15% of what Kredibel reads goes to one queue" | Never measured | No number |
| "Client-side checks warn about a plan limit before anything is read" | Limits are enforced by the server; the upload sheet has no limit check | Server check, Plan & usage shows what is left |
| "Adaptive reading costs about USD 0.45 for a half-year of books" | Measured on the demo company: one reading of 80 documents, 89 pages = USD 0.43 (`run_usage`, `pricing.v1.yaml`) | Kept |
| Every page read twice; Document AI OCR for scans and photos | Built 16 Oct 2026 (spec 022 phase B) | Kept |
| IFRS or US GAAP, switchable on the dashboard | Built (spec 010, `ChartsSection`) | Kept |
| English, Malay and Indonesian dates and formats | Built (`domain/normalize.py`) | Kept |
| Revision history, fonts in amount columns, statement continuity | `M03`, `M04`, `X01` built | Kept |
| Finance Assistant cites the figures it uses | Built; now also quotes the document pages it relied on (spec 022) | Kept, extended |
| — | The demo company and its guided tour (spec 021) were not on the site | New FAQ answer |

Re-run this audit whenever a spec changes status: search the public strings for every feature word
and number, and check each against [`20`](20-implementation-status.md).

## 4. Owner actions (outside the code)

- [x] **Allow the custom domain for sign-in**: done 17 Oct 2026 (`kredibel.app` signs in; `www` only once it exists).
      (adds the domains to the browser key's website restrictions and to Firebase Authentication's
      authorized domains; key changes take up to five minutes). Check:
      a sign-in on `https://kredibel.app` succeeds.
- [ ] **`www.kredibel.app`**: Firebase console → Hosting → *Add custom domain* → `www.kredibel.app`,
      *redirect to* `kredibel.app`; add the records it shows at the DNS host.
- [ ] **Mailbox**: `kredibel.app` has no MX record, so `hello@kredibel.app` (Contact, Privacy, Terms)
      bounces. Add mail forwarding at the DNS host, or change the address in `public.json`.
- [ ] **Terms**: replace the `⟨legal entity⟩` and `⟨governing law⟩` placeholders (`terms.s7Body`).
- [ ] **Budget**: with `MAX_WORKSPACES=200` the worst case is 200 × USD 5/month
      ([`21`](21-cost-analysis.md)); keep the budget alert, and use `SIGNUP_MODE` if sign-ups climb.
- [ ] **After connecting any new domain**: open it in a real browser. Firebase's CDN may keep a
      cached *Site Not Found* page for one `Accept-Encoding` variant; a new Hosting release (clone of
      the live version) clears it.

## 5. Before the submission

The challenge requires five things (rules copied in [`submission/README.md`](submission/README.md)):
a pitch deck on the prescribed template ([content](submission/pitch-deck.md)), a **3 to 4 minute**
video of the working solution ([`submission/demo-video/`](submission/demo-video/), made by
`make video`), the deployed link (it must keep working for the whole evaluation), the GitHub
repository, and a brief description that says how Firebase, Firestore, Cloud Run and Gemini are used
([`submission/brief-description.md`](submission/brief-description.md)). The day-of list:
[`submission/checklist.md`](submission/checklist.md).

- [ ] Spec 012: run the P0 suites on the synthetic books and publish the report; only then quote
      numbers in the README or on the site.
- [ ] T013-18 on the deployed env with a new Google account.
- [ ] The demo company refreshed for the current month if the demo date moves
      (`make demo-template`, spec 021).
- [x] README: what is built, the live URL, the demo account and path, measured demo results, and
      the honest list of what is not built (17 Oct 2026).
- [ ] Pitch deck filled on the prescribed template; video uploaded as a public link; both links in
      the README and the portal.
