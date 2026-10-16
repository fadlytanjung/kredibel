# Tasks 020 — Public site

## Phase 1 — Design foundation

- [x] **T020-01** Public-surface classes + hero motion in `design/mocks/assets/kit.css` from `--k-*`
  variables; `make tokens`; `no_raw_styles` stays green. (AC-020-11)
- [x] **T020-02** `landing()` mock in `tools/design/mocks/screens_more.py`, registered; `make mocks`
  done. `make mock-shots` (the landing screenshots) still to run where Playwright is available.
  (AC-020-1…4)

## Phase 2 — Shared UI

- [x] **T020-03** **TDD** `usePrefersReducedMotion`; `PageMeta` (title/description/OG). (AC-020-11)
- [x] **T020-04** **TDD** `ReadTwiceScene`: `settled` under reduced motion, `play` otherwise; the text
  equivalent states "agreed by two readings". (AC-020-2)
- [x] **T020-05** `StatementSheet`, `ReadingsPair`, `FindingMoment`. (AC-020-2, 4)
- [x] **T020-06** **TDD** `DuplicateDecision`: `Same document` keeps the total, `Different` moves it;
  live-region result; keyboard operable. (AC-020-3)

## Phase 3 — Shell and pages

- [x] **T020-07** `PublicShell`/`PublicHeader`/`PublicFooter`, `tone="dark" | "light"`, signed-in CTA
  switch. (AC-020-8, 9)
- [x] **T020-08** `public.json` namespace + `setup.ts`. (AC-020-11)
- [x] **T020-09** `LandingPage` (hero, live decision, scroll narrative, CTA). (AC-020-1…4)
- [x] **T020-10** `PricingPage` from `contracts/plans.v1.yaml` (no API call). (AC-020-5)
- [x] **T020-11** `HowItWorksPage`, `SecurityPage`, `FaqPage`, `ContactPage`, `PrivacyPage`,
  `TermsPage`. (AC-020-6, 7)
- [x] **T020-12** Copy 3–4 synthetic screenshots into `frontend/public/marketing/`. (AC-020-4)

## Phase 4 — Routing

- [x] **T020-13** Router: public routes; `/` index behaviour (loading → loading, signed-in →
  `/dashboard`, else landing); dashboard at `/dashboard`. (AC-020-1, 9, 10)
- [x] **T020-14** Update `appShellNav.ts` (dashboard path, `isActivePath`, `chromeFor`) and every `/`
  link; update `AppShell` stories/tests, `CreateWorkspaceForm`, `LoginPage`, `NotFoundPage`,
  `Placeholders`, `App.test.tsx`. (AC-020-10)

## Phase 5 — Tests and visual baselines

- [x] **T020-15** Vitest: pages render key headings and CTA targets; router redirects; the hero
  settles under reduced motion; the duplicate decision keeps or moves the total. (AC-020-1…10)
- [x] **T020-16** `tests/visual/public-pages.spec.ts` at 390/834/1440 for `/` and `/pricing` added;
  baselines recorded 15 Oct 2026 (`-darwin.png`, like every other screen's); the six checks pass
  with the suite. (AC-020-11)

## Phase 6 — Docs

- [ ] **T020-17** Update `docs/11` (§3, §4.1, §4.2), `docs/12` (§4, §7, §9, §11), `docs/20`, README
  done. `docs/11` §4.3 screen map and the landing screenshots still to update. (AC-020-10)

## Phase 7 — Revamp: the ledger in depth (plan.md "Revamp")

- [x] **T020-18** Amend spec, plan and tasks (AC-020-2, 4, 12); docs/12 public-site exception (§1, §4,
  §7, §9); docs/11 (route splitting, public widgets); docs/20; mark the landing mock as predating the
  revamp. (AC-020-2, 4, 12)
- [x] **T020-19** Add `motion`; lazy-load the signed-in app, Login and Onboarding behind `Suspense`;
  record the gzip sizes before and after here. (AC-020-11)
  First-load JS (gzip, `vite build`): **335 KB** before (one chunk) → **287 KB** after the split →
  **303 KB** with `motion` and the revamp. Still over the 250 KB budget: the main chunk carries the
  Firebase SDK including Firestore, which `shared/firebase/app.ts` loads eagerly; splitting Firestore
  out of the first load is the next step (not in this spec).
  After merging main (15 Oct 2026): main's AC-010-11 keeps the dashboard and Login in the first
  paint and splits every other app page; with the public pages eager too, first-load JS is
  **232 KB** gzip, inside the budget.
- [x] **T020-20** **TDD** `useInViewAttr`, `useScrollProgress`, `usePointerTilt`: with and without the
  browser APIs; no writes under reduced motion. (AC-020-12)
- [x] **T020-21** `kit.css` foundations: `pub-` stage, depth, reveal, pin rules, lamp, reduced-motion
  overrides; `make tokens`. (AC-020-11, 12)
- [x] **T020-22** **TDD** `ScrollStory`: one DOM, `data-chapter` from progress, chapter headings in
  order, settled when reduced. (AC-020-4, 12)
- [x] **T020-23** `DepthStage`, `PaperArtefact`, `FlowRibbon`, `Lamp`, `Reveal`. (AC-020-2, 12)
- [x] **T020-24** Header pill with the reading-progress rule, full-height mobile menu; footer.
  (AC-020-6, 8, 9)
- [x] **T020-25** Landing hero: depth deck, pointer parallax, the read-twice converge. (AC-020-1, 2)
- [x] **T020-26** Landing reading room (four chapters) and the copy-held section. (AC-020-3, 4)
- [x] **T020-27** Rest of the landing: why, Google Cloud stack, screens, trust, band, closing CTA.
  (AC-020-4)
- [x] **T020-28** Pricing, How it works, Security. (AC-020-5, 6)
- [x] **T020-29** FAQ; **TDD** Contact copy-email button (status live region, no text input);
  Privacy/Terms contents rail. (AC-020-6, 7)
- [ ] **T020-30** Extend `PublicPages.test.tsx`; Playwright with `reducedMotion: 'reduce'`,
  `animations: 'disabled'` and fonts ready; record the baselines (closes T020-16). (AC-020-11)
  Tests extended and the spec updated; the stale landing mock is retired (spec 019, AC-019-1: an
  implemented screen never keeps a deprecated mock); the baselines are still to record on the CI image
  (`make test-visual`), and the axe pass in Storybook is still to run (`make storybook-build`). Lighthouse mobile on `/`
  (15 Oct 2026, production build): performance 80, accessibility, best practices and SEO 100 after the
  finding table got headers and a robots file was added; the open item was CLS 0.15 from the hero's
  animations, fixed by T020-37.
- [x] **T020-31** After merging main (specs 005, 010, 011, 018, 019): the product screenshots come
  from the app's synthetic preview routes (`npm run marketing:shots`, `tests/marketing/`, the parity
  fixtures of spec 019) instead of copies of the mock shots; copy follows the shipped product (ledger
  columns proposed by code with the model as fallback, the dashboard's profit and loss flow, the
  assistant's cited answers); the unused `landing.how` copy is removed. (AC-020-4, 6)
- [x] **T020-32** Copy audit against what is built (16 Oct 2026, [`docs/24`](../../24-submission-checklist.md)
  §3): screening, workspace deletion, team members, the unmeasured match and review numbers and the
  client-side limit check are corrected; the reading cost is kept as measured; a ninth FAQ answer
  introduces the demo company. (AC-020-4, 6)

## Phase 8 — SEO (plan.md "SEO")

- [x] **T020-33** Amend spec (AC-020-13), plan, docs/11 (SEO), docs/16 §6.2 (`VITE_SITE_URL`),
  docs/20. (AC-020-13)
- [x] **T020-34** **TDD** `publicSite.ts` and `shared/config/seo.ts` + `build/seoPlugin.ts`: head tags, JSON-LD, sitemap and robots
  builders; the build plugin; the router's public routes match the list. (AC-020-13)
- [x] **T020-35** **TDD** `PageMeta`: canonical, Open Graph, Twitter, `noindex`, and the
  `data-prerendered` tags removed on mount; every public page passes its path; the 404 page is
  `noindex`. (AC-020-13)
- [x] **T020-36** **TDD** the Cloud Run origin serves `<path>.html`; the 1200×630 social card.
  (AC-020-13)
- [x] **T020-37** Measure and fix the landing's layout shift (< 0.1); product images declare their
  size; Lighthouse mobile on `/` recorded. (AC-020-13)
  16 Oct 2026, production build, `layout-shift` observer on `/`: before 0.017 at 1440 px and 0.038 at
  390 px (the scan sweep, the headline's width axis and others; see plan.md "SEO"), after 0.000 at
  both widths and 0.001 with the CPU slowed 4×. Lighthouse on the deployed site is still to re-run
  once `kredibel.app` serves this build.
