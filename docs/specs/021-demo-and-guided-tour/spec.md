# Spec 021 — Demo company and guided tour

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 (submission demo) |
| **Owner role** | B: Backend (copy), C: Frontend (onboarding choice, tour) |
| **Depends on** | 002 (demo books), 013 (workspace creation), 016 and 017 (labels and runs to show) |
| **Requirements** | FR-013, NFR-13, NFR-14 |
| **Design** | [`docs/12`](../../12-design-system.md); mocks `onboarding.html` and `tour.html` |

## Summary

A person who signs up to see Kredibel should not have to collect bank statements first. The server
keeps one **demo template workspace**: Sunrise Coffee Roasters, whose synthetic books (docs/18 §5,
April to September 2026) were read, checked and reconciled once by the real workflows, so it holds
documents, bank lines, invoices, receipts, the ledger, months, matches, findings, review items,
clients and suppliers, labels and runs. On onboarding a person can choose **Explore a demo company**:
the server copies the template into a new workspace that the person owns, in seconds and with no
model call. A **guided tour** then walks through every menu, highlighting one part of each page with
a short explanation and Next, Back and Skip.

## User stories

### US-021-1: Open a demo company (new person)

- **AC-021-1** Given the server has a demo template (`DEMO_TEMPLATE_ORG`) and I am signed in without
  a workspace, when I choose **Explore a demo company** on onboarding, then a new workspace is created
  with me as owner, with the template's name, entity type, profile, country, time zone and currency,
  on the default plan's free trial, holding a copy of every record of the template (every collection
  under `orgs/{template}` and `orgPrivate/{template}`, and every file under `orgs/{template}/` in
  Cloud Storage), and I land on the dashboard. The template is never changed.
- **AC-021-2** A copy keeps its meaning: the template's workspace ID and its people become the new
  workspace and me, in IDs and in fields; members, invites, audit events, assistant threads and
  usage counters are not copied (the copy counts against no limit); one `WORKSPACE_CREATED` and one
  `DEMO_COPIED` event are written. If the copy fails, what was copied is removed and nothing is left
  half made.
- **AC-021-3** The choice appears only when the server has a template (`demoAvailable` on
  `GET /api/me`); the rules for a new workspace apply (closed signup, the workspace limit, one
  workspace per person). `POST /api/workspaces/demo` returns `201` with the workspace, `409
  ALREADY_IN_WORKSPACE` when I have one and `503 DEMO_UNAVAILABLE` without a template.

### US-021-2: Learn the product by walking through it (any new owner)

- **AC-021-4** After a workspace is created (a demo or my own), the dashboard starts a guided tour: a
  highlighted part of the page and a card with the step's title, one or two sentences, "Step n of m",
  **Back**, **Next** and **Skip the tour**. The steps follow the menu: the dashboard's period and
  figures, where the money went, the upload tray, reconciliation, the review queue, risk, labels, runs
  (owners only), the assistant, and an ending card. Each step opens its page
  first; a step whose part is not on the page shows its card without a highlight.
- **AC-021-5** **Skip the tour**, Esc or **Done** ends it and records it for the person (`POST
  /api/me/tour`; `tourSeen` on `GET /api/me`): the tour starts by itself for anyone who has not seen
  it, which is right after onboarding, once per person on any device, and can be started again with
  **Take the tour** in the top bar. On the demo
  company the dashboard steps show the months that have books.
- **AC-021-6** The tour works from 360 to 1600 px (on phones the card sits at the bottom and the part
  is scrolled into view), with the keyboard (Tab stays in the card, arrows move, Esc ends), with a
  screen reader (a labelled dialog that announces each step), and without motion when motion is
  reduced. Its words live in the locale.

### US-021-3: Keep the template current (operator)

- **AC-021-7** `make demo-template` seeds the template workspace and reads the demo books shifted to
  end last month through the real workflows; docs/16 names `DEMO_TEMPLATE_ORG`, docs/18 the books.

## Out of scope

- Resetting a demo workspace in place (sign up again instead); a demo inside an existing workspace.
- Copying nested collections below a record (only assistant messages exist, and threads are not
  copied).

## Edge cases

- Two clicks: the second finds the workspace the first made (`409`, the claims are re-set).
- A template without documents copies an empty workspace with its profile.
- The template's account hashes stay as they are: within the copy they still match one another.
