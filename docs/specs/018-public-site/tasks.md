# Tasks 018 — Public site

## Phase 1 — Design foundation

- [x] **T018-01** Public-surface classes + hero motion in `design/mocks/assets/kit.css` from `--k-*`
  variables; `make tokens`; `no_raw_styles` stays green. (AC-018-11)
- [x] **T018-02** `landing()` mock in `tools/design/mocks/screens_more.py`, registered; `make mocks`
  done. `make mock-shots` (the landing screenshots) still to run where Playwright is available.
  (AC-018-1…4)

## Phase 2 — Shared UI

- [x] **T018-03** **TDD** `usePrefersReducedMotion`; `PageMeta` (title/description/OG). (AC-018-11)
- [x] **T018-04** **TDD** `ReadTwiceScene`: `settled` under reduced motion, `play` otherwise; the text
  equivalent states "agreed by two readings". (AC-018-2)
- [x] **T018-05** `StatementSheet`, `ReadingsPair`, `FindingMoment`. (AC-018-2, 4)
- [x] **T018-06** **TDD** `DuplicateDecision`: `Same document` keeps the total, `Different` moves it;
  live-region result; keyboard operable. (AC-018-3)

## Phase 3 — Shell and pages

- [x] **T018-07** `PublicShell`/`PublicHeader`/`PublicFooter`, `tone="dark" | "light"`, signed-in CTA
  switch. (AC-018-8, 9)
- [x] **T018-08** `public.json` namespace + `setup.ts`. (AC-018-11)
- [x] **T018-09** `LandingPage` (hero, live decision, scroll narrative, CTA). (AC-018-1…4)
- [x] **T018-10** `PricingPage` from `contracts/plans.v1.yaml` (no API call). (AC-018-5)
- [x] **T018-11** `HowItWorksPage`, `SecurityPage`, `FaqPage`, `ContactPage`, `PrivacyPage`,
  `TermsPage`. (AC-018-6, 7)
- [x] **T018-12** Copy 3–4 synthetic screenshots into `frontend/public/marketing/`. (AC-018-4)

## Phase 4 — Routing

- [x] **T018-13** Router: public routes; `/` index behaviour (loading → loading, signed-in →
  `/dashboard`, else landing); dashboard at `/dashboard`. (AC-018-1, 9, 10)
- [x] **T018-14** Update `appShellNav.ts` (dashboard path, `isActivePath`, `chromeFor`) and every `/`
  link; update `AppShell` stories/tests, `CreateWorkspaceForm`, `LoginPage`, `NotFoundPage`,
  `Placeholders`, `App.test.tsx`. (AC-018-10)

## Phase 5 — Tests and visual baselines

- [x] **T018-15** Vitest: pages render key headings and CTA targets; router redirects; the hero
  settles under reduced motion; the duplicate decision keeps or moves the total. (AC-018-1…10)
- [ ] **T018-16** `tests/visual/public-pages.spec.ts` at 390/834/1440 for `/` and `/pricing` added;
  baselines still to record on the CI image (`make test-visual`). (AC-018-11)

## Phase 6 — Docs

- [ ] **T018-17** Update `docs/11` (§3, §4.1, §4.2), `docs/12` (§4, §7, §9, §11), `docs/20`, README
  done. `docs/11` §4.3 screen map and the landing screenshots still to update. (AC-018-10)

## Phase 7 — Revamp: the ledger in depth (plan.md "Revamp")

- [x] **T018-18** Amend spec, plan and tasks (AC-018-2, 4, 12); docs/12 public-site exception (§1, §4,
  §7, §9); docs/11 (route splitting, public widgets); docs/20; mark the landing mock as predating the
  revamp. (AC-018-2, 4, 12)
- [x] **T018-19** Add `motion`; lazy-load the signed-in app, Login and Onboarding behind `Suspense`;
  record the gzip sizes before and after here. (AC-018-11)
  First-load JS (gzip, `vite build`): **335 KB** before (one chunk) → **287 KB** after the split →
  **303 KB** with `motion` and the revamp. Still over the 250 KB budget: the main chunk carries the
  Firebase SDK including Firestore, which `shared/firebase/app.ts` loads eagerly; splitting Firestore
  out of the first load is the next step (not in this spec).
- [x] **T018-20** **TDD** `useInViewAttr`, `useScrollProgress`, `usePointerTilt`: with and without the
  browser APIs; no writes under reduced motion. (AC-018-12)
- [x] **T018-21** `kit.css` foundations: `pub-` stage, depth, reveal, pin rules, lamp, reduced-motion
  overrides; `make tokens`. (AC-018-11, 12)
- [x] **T018-22** **TDD** `ScrollStory`: one DOM, `data-chapter` from progress, chapter headings in
  order, settled when reduced. (AC-018-4, 12)
- [x] **T018-23** `DepthStage`, `PaperArtefact`, `FlowRibbon`, `Lamp`, `Reveal`. (AC-018-2, 12)
- [x] **T018-24** Header pill with the reading-progress rule, full-height mobile menu; footer.
  (AC-018-6, 8, 9)
- [x] **T018-25** Landing hero: depth deck, pointer parallax, the read-twice converge. (AC-018-1, 2)
- [x] **T018-26** Landing reading room (four chapters) and the copy-held section. (AC-018-3, 4)
- [x] **T018-27** Rest of the landing: why, Google Cloud stack, screens, trust, band, closing CTA.
  (AC-018-4)
- [x] **T018-28** Pricing, How it works, Security. (AC-018-5, 6)
- [x] **T018-29** FAQ; **TDD** Contact copy-email button (status live region, no text input);
  Privacy/Terms contents rail. (AC-018-6, 7)
- [ ] **T018-30** Extend `PublicPages.test.tsx`; Playwright with `reducedMotion: 'reduce'`,
  `animations: 'disabled'` and fonts ready; record the baselines (closes T018-16). (AC-018-11)
  Tests extended and the spec updated; the baselines are still to record on the CI image
  (`make test-visual`), and the axe pass in Storybook is still to run (`make storybook-build`).
