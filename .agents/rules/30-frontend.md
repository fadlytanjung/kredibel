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
- Styling: Tailwind utilities with tokens from `docs/12-design-system.md`; inline styles only for
  computed geometry (bbox overlays, chart sizes).
- Money/dates only via `MoneyText`, `DateText`, `formatMoney`, `formatDate`; numbers use the `num`
  utility (tabular) and are right-aligned in tables.
- Severity and verdicts: colour + icon + text, never colour alone.
- Markdown (memo, assistant) only through `SafeMarkdown` (no raw HTML). Citation markers become
  `CitationChip`s.
- Every data panel has loading, empty and error states.
- User-visible strings only in `src/shared/i18n/locales/en/*.json`, read with `useTranslation()`; the
  ESLint rule `i18next/no-literal-string` must pass. English is the only selectable language; others
  appear as "Coming soon".
- Coming-soon plans, languages and features are rendered visible and disabled (`ComingSoonBadge`),
  never clickable.
- Plan limits: show them before the user hits them (`UsageMeter`, disabled reasons) and handle
  `403 PLAN_LIMIT_REACHED` / `TRIAL_EXPIRED` with the `PlanLimitDialog`.
- Never render a full account or ID number; use `MaskedText`.
- Tests: Vitest + Testing Library + MSW; axe checks for new components.
