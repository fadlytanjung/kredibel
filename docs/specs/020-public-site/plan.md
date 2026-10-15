# Plan 020 — Public site

## Approach

React-first: build the public pages as SPA routes on the existing tokens and `kit.css` (ADR-019). The
dashboard moves from `/` to `/dashboard` so `/` can be the public landing; every other app route keeps
its path. A new `PublicShell` (tone-aware header + footer) wraps the public pages; `PageMeta` sets the
document title and description per page (React 19 renders `<title>`/`<meta>` natively). All copy lives
in `locales/en/public.json`. One HTML mock (`design/mocks/landing.html`) is generated for the landing
only; the other public pages rely on Storybook stories and Playwright baselines.

No backend change: the SPA catch-all serves every path, and the security headers already allow
self-hosted images and the kit stylesheet.

## Design direction (see docs/12)

The landing hero **performs** "read twice": a printed statement figure with the **AI reader** mark and
the **witness** mark converging on it and a **double rule** snapping under the value, on the brand's
ink ledger-paper surface (the same surface as onboarding/login). One live **duplicate decision**
follows; the rest is a scroll narrative. Only the product's own devices are used (the k-tick mark, the
double/dotted/wavy reading rules, the violet lamp, Archivo's width axis, ink ledger paper) — no
gradients, illustrations or stock photos. *Superseded for the public site by the revamp below.*

## Files

- `design/mocks/assets/kit.css` — public-surface classes (`.site*`, `.hero*`, `.statement*`,
  `.read-twice`, `.decision*`, `.section*`, `.prose`, `.faq`, `.pricing` reuses `.plans`) and the hero
  motion; `make tokens` copies it to `frontend/src/app/styles/kit.css`.
- `tools/design/mocks/screens_more.py` — `landing()` screen; registered in `SCREENS_MORE`/`NOTES_MORE`.
- `frontend/src/shared/i18n/locales/en/public.json` + `setup.ts` — the `public` namespace.
- `frontend/src/shared/lib/usePrefersReducedMotion.ts` — motion preference hook (used by the hero).
- `frontend/src/shared/ui/PageMeta.tsx`, `ReadTwiceScene.tsx`, `StatementSheet.tsx`,
  `ReadingsPair.tsx`, `DuplicateDecision.tsx`, `FindingMoment.tsx` — one folder each, stories + tests.
- `frontend/src/widgets/PublicShell.tsx` (+ `PublicHeader.tsx`, `PublicFooter.tsx`).
- `frontend/src/pages/public/` — `LandingPage.tsx`, `PricingPage.tsx`, `HowItWorksPage.tsx`,
  `SecurityPage.tsx`, `FaqPage.tsx`, `ContactPage.tsx`, `PrivacyPage.tsx`, `TermsPage.tsx`.
- `frontend/src/app/router.tsx` — public routes, `/` index behaviour, dashboard at `/dashboard`.
- `frontend/src/shared/ui/appShellNav.ts` and the `/` links (LoginPage, NotFoundPage, Placeholders,
  CreateWorkspaceForm, AppShell stories/tests).
- `frontend/public/marketing/` — synthetic screenshots copied from `docs/assets/mocks/`.

## Revamp: "the ledger in depth" (2026-10, T020-18…30)

The first cut stacked identical section heads and cards. The revamp makes the public site immersive:
a dark, deep **reading room** where the product's own paper artefacts float in 3D and the visitor
scrolls *through* them while Kredibel reads them twice, holds a copy, catches a forged balance and
reconciles the month. Every animation performs a real product act (scan beam, converging reading
marks, double rule, violet evidence lamp, ledger lines drawing into a money flow).

- **Visual freedom on the public site only.** Gradients, glows and decorative shapes are allowed on
  `pub-*` surfaces (built with `color-mix()` of existing tokens); the app's rules in docs/12 §1 are
  unchanged. Still no stock photos, emoji or third-party illustration.
- **3D is CSS.** `perspective` + `preserve-3d` + `translateZ`; structure is clip wrapper
  (`overflow: clip`) → perspective stage → `preserve-3d` group → leaves; opacity/filter only on leaves.
- **`motion` (hooks only).** `useScroll`, `useSpring`, `useMotionValueEvent` drive scroll progress and
  pointer tilt; the hooks write CSS custom properties (`--p`, `--rx`, `--ry`, `--lx`, `--ly`) on the
  element that uses them, inside effects or motion-value callbacks. No `motion.*` components (their
  `style` prop would break `no_raw_styles`, and they cost ~20 KB more).
- **No `position: fixed`.** `.viewport` is a size container (the containing block for fixed
  children), so the header pill, progress rule and pinned stage are `sticky`.
- **Pinning** only at `@container app (width >= 1024px)` and `@media (min-height: 640px) and
  (prefers-reduced-motion: no-preference)`; otherwise stacked and settled (covers 200 % zoom).
- **One DOM per section; decorative layers carry no text** (`aria-hidden`, shapes only), so no
  string is duplicated for assistive technology or tests.
- **Budget.** The single chunk was ~330 KB gzip before the revamp (over the 250 KB budget). Public
  pages stay eager (the landing h1 renders synchronously); the signed-in app, Login and Onboarding are
  lazy-loaded behind `Suspense`. Sizes before and after are recorded in `tasks.md` (T020-19).
- **Cut:** route view transitions (`viewTransition` needs a data router; the app uses
  `BrowserRouter`), a magnetic cursor, rotated-text carousels, and a second pinned story.

New files: `frontend/src/shared/lib/{useInViewAttr,useScrollProgress,usePointerTilt}.ts` and
`frontend/src/widgets/public/` (`DepthStage`, `PaperArtefact`, `ScrollStory`, `FlowRibbon`, `Lamp`,
`Reveal`). `FlowRibbon` is a decorative money flow; the name `MoneyFlow` stays reserved for the
dashboard Sankey (docs/12 §6.4).

## Risks

- **Route move ripple:** one focused change updates the nav model, links, stories and tests.
- **JS budget:** only `motion` hooks (~10–15 KB gzip); split the signed-in app out of the first load.
- **Styles gate:** everything through `kit.css`/tokens; no arbitrary Tailwind values or inline styles.

## Verification

`make check` (lint, tsc, boundaries, `no_raw_styles`, tokens-check, repo checks, tests),
`make test-visual` with the new baselines (recorded with `reducedMotion: 'reduce'` so scenes are settled), `make storybook-build`. Manual: `/` logged out shows the
landing; `/` signed in redirects to `/dashboard`; axe clean on the public pages.
