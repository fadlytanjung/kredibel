# ADR-019 — One component stylesheet for the mocks and the app

**Status:** Accepted · **Date:** 2026-10-11 · **Supersedes:** the "React rebuilds kit.css with Tailwind"
rule of [`12`](../12-design-system.md) §0

## Context

The high-fidelity mocks in `design/mocks/` are the agreed design. Their components live in
`design/mocks/assets/kit.css`, which uses about 530 pixel values: some 20 font sizes, weights such as
580, 620 and 640, font widths such as 116%, and component sizes. The rule was that the React app
rebuilds each kit class with Tailwind utilities and tokens only, while the raw-style gate forbids
arbitrary Tailwind values. The tokens have no matching scale, so an exact rebuild was impossible and
every hand translation drifted: the first screens built for spec 001 and spec 013 did not look like
their mocks. The mocks also draw their own icon set, while the app used lucide-react.

## Decision

`design/mocks/assets/kit.css` is **the** component stylesheet, for the mocks and the app.

- `make tokens` copies it to `frontend/src/app/styles/kit.css` (generated; the `@font-face` is
  dropped because the app loads the same Archivo variable font from `@fontsource-variable/archivo`)
  and `make tokens-check` fails when the copy is stale.
- `src/index.css` imports it into Tailwind's `components` layer, so utilities can still adjust layout.
- React components in `shared/ui/` render the kit class names; `cva` variants map to kit modifier
  classes (`button button-primary button-lg`). Pages and widgets reproduce the mock's markup
  (`tools/design/mocks/screens.py`) with kit classes and add Tailwind only for layout glue the kit
  does not have.
- The mock icon set (`tools/design/mocks/icons.py`) is generated into
  `frontend/src/shared/ui/icons.generated.ts` and drawn by `shared/ui/Icon`. lucide-react is removed.
- A visual change is made in `kit.css` (and `screens.py` for layout), then `make tokens mocks
  mock-shots`, then the app's visual baselines are updated in the same change.

## Alternatives considered

| Option | Why not |
|---|---|
| Add a full type and size scale to the tokens and keep rebuilding in Tailwind | Exact only while two copies are kept in step by hand; drift returns with the next kit change |
| Tailwind arbitrary values for kit's sizes | The raw-style gate exists to stop exactly that; values would be scattered over components |
| CSS modules per component, copied from kit.css | Same two-copies problem, smaller files |

## Consequences

- The app looks like the mocks by construction, at every width, because the same container queries
  (`@container app`) apply: pages render inside `.viewport` / `.app` like the mocks.
- Values in `kit.css` still come from `tokens.css` variables except the documented exceptions (the
  synthetic statement page); `tools/checks/no_raw_styles.py` keeps guarding `frontend/src` and
  exempts the two generated files.
- Mock-only helpers (index and brand pages) ship in the app's CSS; about 20 kB gzip in total.
- Storybook and the Playwright baselines show kit-styled components; the baselines were re-recorded.
