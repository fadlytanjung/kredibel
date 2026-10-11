---
trigger: glob
globs: frontend/**
description: Frontend conventions for the Kredibel React app.
---

# Frontend conventions

- React 19 + Vite + TypeScript strict (`noUncheckedIndexedAccess`); no `any`; named exports only.
- Feature-Sliced Design: `app → pages → widgets → features → entities → shared`; import only downward
  (eslint-plugin-boundaries).
- API types come from `src/shared/api/schema.d.ts` generated from `contracts/openapi.yaml`
  (`npm run gen:api`). Never hand-write API types.
- Server state only through TanStack Query hooks in `entities/*/api.ts`. Firestore listeners are a
  change signal that invalidates queries; data comes from the API.
- Styling (ADR-019): components render the classes of `design/mocks/assets/kit.css` (copied into the
  app by `make tokens`) and icons through `shared/ui/Icon`; pages reproduce the mock's markup from
  `tools/design/mocks/screens.py`. Tailwind utilities from the tokens only for layout glue; no raw
  colours, arbitrary values or inline styles except computed geometry; `tools/checks/no_raw_styles.py`
  enforces it. A visual change goes into `kit.css` first. Use the `/ui-screen` skill.
- Information architecture: the dashboard summarizes and links; tables live on their own pages
  (Documents, Reconciliation, Review, Risk). Do not put tables on the dashboard or KPIs on table pages.
- Every screen works from 360 to 1600 px: window classes from tokens, container queries inside
  components, touch targets ≥ 44 px, no horizontal page scroll; charts have a table alternative.
- Money/dates only via `MoneyText`, `DateText`, `formatMoney`, `formatDate`; numbers use the `num`
  utility (tabular) and are right-aligned in tables.
- Severity and verdicts: colour + icon + text, never colour alone.
- Markdown (explanations, assistant) only through `SafeMarkdown` (no raw HTML). Citation markers
  `[[…]]` become `CitationChip`s.
- Every data panel has loading, empty and error states.
- User-visible strings only in `src/shared/i18n/locales/en/*.json`, read with `useTranslation()`; the
  ESLint rule `i18next/no-literal-string` must pass. English is the only selectable language; others
  appear as "Coming soon".
- Coming-soon plans, languages and features are rendered visible and disabled (`ComingSoonBadge`),
  never clickable.
- Plan limits: show them before the user hits them (`UsageMeter`, disabled reasons) and handle
  `403 PLAN_LIMIT_REACHED` / `TRIAL_EXPIRED` with the `PlanLimitDialog`.
- Never render a full account or tax ID number; use `MaskedText`.
- Tests: Vitest + Testing Library + MSW; a Storybook story per component state with axe; Playwright
  visual baselines at 390/834/1440 px change only in a reviewed commit.
- The Labels page and the Runs page are data tables with their own routes; a label decision goes
  through `features/decide-label/` only, and prompt or response text is shown only when the API says
  content is captured.
- Charts fill the full width of the content column (no chart shares a row with another panel); the
  money flow offers Flow, By month and Statement views and follows the workspace's accounting framework.
