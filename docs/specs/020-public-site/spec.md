# Spec 020 — Public site (landing and public pages)

| | |
|---|---|
| **Status** | Ready |
| **Priority** | P0 (submission) |
| **Owner role** | C: Frontend (with D for routing/hosting) |
| **Depends on** | 001 (shell, tokens, router), 013 (plans copy) |
| **Requirements** | FR-020, NFR-13, NFR-14, NFR-15 |
| **Design** | [`docs/12`](../../12-design-system.md) §1, §4, §6, §9, §12; no HTML mock: the first one was retired with the revamp under spec 019's parity rule, and the React pages are the reference |

## Summary

Kredibel today has one public route, `/login`; every other route is auth- or workspace-guarded, so a
visitor (or a judge) opening the deployed URL is bounced to sign-in and never sees what the product
is. This spec adds a real, logged-out front door: a marketing **landing page at `/`** and a small set
of **public pages** (Pricing, How it works, Security & trust, FAQ, Contact, Privacy Policy, Terms of
Service). They are React routes in the same SPA (ADR-018), English, on the existing design tokens and
`kit.css` (ADR-019). The landing **performs** the product's core idea — *read twice* — rather than
describing it, so a first-time visitor understands it in seconds.

## User stories

### US-020-1: Understand the product without signing in (visitor)

- **AC-020-1** Given no session, when I open `/`, then I see the landing page (not a redirect to
  `/login`), with the tagline "Every number has a source.", one sentence naming the product and the
  three catches (duplicates, edited documents, unmatched payments), and the primary **Start free
  trial** action.
- **AC-020-2** The landing hero shows one printed statement figure with the two reading marks (AI
  reader and witness) and a **double rule** under the value, set in a **3D depth scene**: the
  product's own paper artefacts (statement, invoice, receipt, ledger export) float at different
  depths behind it. The hero copy, the statement rows, a single scan sweep and the two converging
  readings arrive in one staggered sequence; afterwards a quiet ambient loop (≥ 1.6 s, decorative)
  keeps the scene alive, and on a fine pointer the scene tilts and a violet lamp follows the cursor.
  A `prefers-reduced-motion: reduce` visitor sees the same figure already settled, with the two
  reading labels as static chips and no animation at all.
- **AC-020-3** Below the hero, a live **duplicate decision** shows the same statement held
  (`ACB_Feb_2026 (1).pdf`); choosing **Same document** keeps the running total and stamps "Kept as a
  copy", choosing **Different** counts it and moves the total. The control is keyboard-operable and
  the result is announced in a live region.
- **AC-020-4** The page continues as an immersive scroll narrative. First **the reading room**: four
  chapters (any order → read twice → forensics with the lamp → the month reconciles and the money
  flows), pinned with a progress rail on wide, tall screens and stacked elsewhere; each chapter has a
  real heading. Then the live duplicate decision (AC-020-3, never inside the pinned stage), *why
  Kredibel* (the problem and what Kredibel does instead), *built on Google Cloud* (the service stack),
  the product's screens with the two readings of one value, the trust rules, a plans and questions
  band, and a closing call to action before the footer.

### US-020-2: Find the legal, pricing and help pages (visitor)

- **AC-020-5** `/pricing` lists the free trial as available (from `contracts/plans.v1.yaml`) and
  Starter, Professional and Enterprise as **Coming soon**, with no price and no purchase action; two
  coming-soon features are shown. It does not call `GET /api/plans` (which requires a token).
- **AC-020-6** `/how-it-works`, `/security`, `/faq`, `/contact`, `/privacy` and `/terms` each render
  without a session, are reachable from the header and footer, and are deep-linkable (a direct URL
  load works).
- **AC-020-7** Contact shows a mailto link and the operating name; the Privacy Policy and Terms state
  that demos use synthetic data, that real-data controls are on, that processing is on Google Cloud /
  Firebase, that the service is a free trial with no billing, and that it gives no financial advice.
  Legal entity and governing law are marked placeholders.

### US-020-3: Sign in from the landing (visitor → user)

- **AC-020-8** **Sign in** and **Start free trial** both lead to `/login`; after signing in, a user
  with a workspace lands on the dashboard and a user without one lands on `/onboarding`.
- **AC-020-9** Given a signed-in user, when they open `/`, then they are redirected to `/dashboard`;
  other public pages remain viewable and show **Go to dashboard** instead of the trial action.

### US-020-4: The app keeps working (user)

- **AC-020-10** The dashboard moves from `/` to `/dashboard`; Documents, Reconciliation, Review, Risk,
  Clients and suppliers, Assistant, Labels, Runs and Settings keep their current paths; the shell
  logo, home and back links point to `/dashboard`.
- **AC-020-11** Every public page is responsive from 360 px to 1600 px, sets its own title and
  description (`PageMeta`), passes axe with no serious/critical violations, and uses only tokens and
  `kit.css` (no raw styles).
- **AC-020-12** Motion on the public site is depth and scroll, never scroll hijack: 3D is CSS
  transforms (no WebGL); scroll-linked and pointer effects come from `motion` hooks writing CSS
  custom properties; pointer effects only on a fine pointer; decorative 3D layers carry no text and
  are hidden from assistive technology; under `prefers-reduced-motion` every scene is settled and
  nothing pins or moves; at 200 % zoom or under 1024 px wide the narrative is stacked, not pinned.
- **AC-020-13** Search engines and link previews get each public page without running JavaScript:
  the build writes one HTML file per public route whose `<head>` carries that page's title,
  description, canonical URL on `VITE_SITE_URL` (default `https://kredibel.app`), Open Graph and
  Twitter card with a 1200×630 social image, and JSON-LD (Organization, WebSite and
  SoftwareApplication on `/`, FAQPage on `/faq`, WebPage everywhere). `sitemap.xml` lists the public
  pages and `robots.txt` names it; the 404 page is `noindex`. In the app the head never holds two
  titles or canonicals, and the landing's cumulative layout shift stays under 0.1 (amended
  2026-10-16, T020-33).

## Out of scope

- No billing, checkout or real prices; paid plans stay "coming soon".
- No backend endpoints, no contact-form backend, no CMS — copy lives in `locales/en/public.json`.
- No new languages (English only), no dark theme, no analytics. No body prerender or SSG: only the
  `<head>` of each public route is written at build time (AC-020-13).
- No smooth-scroll or scroll-hijack library and no WebGL; `motion` is the only animation dependency
  and only its hooks are used (amended 2026-10-14, T020-18).

## Edge cases

- A signed-in visitor with an expired/absent workspace claim still sees public pages; `/` redirects
  to `/dashboard`, which redirects on to `/onboarding`.
- `prefers-reduced-motion` and `200%` zoom must both leave the hero readable.
- Deep links to any public path work through the SPA catch-all (no server changes).
