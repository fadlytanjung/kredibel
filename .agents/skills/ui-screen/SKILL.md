---
name: ui-screen
description: Designs, builds or improves a Kredibel screen or UI component the same way every time — spec, mock, screenshots at three widths, critique, then React components with stories and visual baselines. Use when adding or changing a page, widget, component, chart, the logo or any visual detail, or when asked to make the UI look better.
---

# Design or change a screen

The design has one source of truth per layer: tokens in `contracts/design/tokens.json`, component
styles in `design/mocks/assets/kit.css` for both the mocks and the app (ADR-019; `make tokens` copies
it), component behaviour in `frontend/src/shared/ui/`, screens in `tools/design/mocks/screens.py`
(mocks) whose markup `frontend/src/pages|widgets/` reproduces with the same classes. Rules live in
`docs/12-design-system.md`; screen behaviour in `docs/11-frontend.md` §4–§6. Change the lowest layer
that fixes the problem.

## Steps

1. **Read the brief.** The spec's acceptance criteria, `docs/11-frontend.md` for the screen (route,
   data, states, responsive row in §5a) and `docs/12-design-system.md` §1 (principles and *What we
   avoid*), §5 (window classes, container rules), §6 (signature elements), §8 (content style).
2. **Write the words first.** The status sentence or title, labels, button names (an action keeps its
   name through the flow), empty and error states. Plain, sentence case, no alarm words; name the
   money ("IDR 18,700,000 on 9 Feb fits two invoices").
3. **Mock it.** Add or change the screen function in `tools/design/mocks/screens.py` using the shell
   (`shell`, `topbar`) and existing kit classes. New visual pattern → add a class to `kit.css` that
   uses only `--k-*` variables; a new value → add a token first and run `make tokens`. Synthetic data
   only (`docs/18-synthetic-data.md`), consistent with the other mocks (the same totals, counts and
   names everywhere).
4. **Render and look.** `make mocks mock-shots`, then open `docs/assets/mocks/<screen>-mobile.png`,
   `-tablet.png` and `-desktop.png` and check:
   - one loud thing; nothing in ALL CAPS, no middle-dot strings, no arrows after link text, no
     one-word colour accents in headings, no identical card grids;
   - numbers tabular and right-aligned, units small and muted, reading marks on printed figures;
   - severity as colour + icon + text; mint only for "checked";
   - no horizontal page scroll at 360 px; targets ≥ 44 px; the bottom nav and upload button never
     cover the primary action;
   - counts and totals agree with the other screens.
   Fix and repeat until all three widths pass. Note what was tried in the PR description.
5. **Build it.** Components in `frontend/src/shared/ui/` with `cva` variants and a story per state
   (default, loading, empty, error, each size class); widgets and pages compose them and set no
   colours, sizes or shadows. Strings in `locales/en/*.json`.
6. **Prove it.** Vitest + Testing Library for behaviour, Storybook axe, and a Playwright spec in
   `frontend/tests/visual/` that serves the screen's shared fixture (`contracts/design/fixtures/`)
   to its dev preview route, compares the visible outline of mock and screen at 390/834/1440,
   records the baselines (updated only in this reviewed change), checks the 360/1600 bounds and
   runs axe (`.agents/rules/35-ui-sync.md`). Add the screen, state or drawer to
   `tools/design/mocks/inventory.py`; mark what is not built as planned. Then
   `tools/checks/no_raw_styles.py` and `make check`.
7. **Keep the docs true.** Update `docs/11-frontend.md` (behaviour), `docs/12-design-system.md`
   (a new rule, token role or component), the screenshot links, and the flow diagrams in
   `docs/11-frontend.md` §4.3–§5.3 if navigation changed.

## Logo changes

Edit the SVGs in `design/brand/` by hand on the 64-unit grid of `docs/12-design-system.md` §9; keep
the stem, tick and tile proportions; regenerate the favicon variant; rebuild the brand page with
`make mocks mock-shots`.
