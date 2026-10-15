---
trigger: always_on
description: Keep every UI change aligned with the generated mocks and implementation.
---

# UI changes are one SDD deliverable

- Every UI change has a spec/task and updates the affected mock source in
  `tools/design/mocks/` and React implementation in the same change. This includes wording,
  navigation, responsive behaviour, loading, empty, error and success states.
- Change component styles in `design/mocks/assets/kit.css`, values in
  `contracts/design/tokens.json`, and words in `frontend/src/shared/i18n/locales/en/`.
  Do not edit generated HTML or `frontend/src/app/styles/kit.css` directly. A mock uses the kit's
  classes only, never Tailwind utilities the kit does not define; a component uses the same kit
  classes as its mock.
- **Every screen has an inventory entry** in `tools/design/mocks/inventory.py` (route, status,
  spec). A state, drawer or overlay of an implemented screen is its own mock and entry; a design
  for something not built is `DESIGN_ONLY`, and a part of an implemented screen that is not built
  yet is marked planned inside the mock (`data-planned="TNNN-xx"`, a "Planned" badge) with its
  task. Nothing in a mock may look implemented when it is not.
- **Mock and screen share one synthetic fixture** (`contracts/design/fixtures/*.json`): the mock
  generator reads it and the app's own locale words; the browser check serves it as the API.
  New numbers, names or states go into the fixture, never into the mock alone.
- **Parity is proven in the browser**, not by eye alone: a Playwright spec in
  `frontend/tests/visual/` serves the fixture to the dev preview route (`frontend/src/app/
  ShellPreview.tsx`), compares the visible outline (headings, tabs, chips, columns, controls,
  actions) of the screen with its mock at 390, 834 and 1440 px, records the screenshot
  baselines, checks the 360 and 1600 px bounds (no horizontal scroll, usable targets, keyboard)
  and runs axe (no serious or critical violation). A change to a screen updates its spec and
  baselines in the same change; baselines are never re-recorded to hide a difference.
- Run `make tokens mocks` and `make mock-shots` for the affected screens; inspect the screenshots
  at 390/834/1440 px. Run `make check`, including `tools/checks/mock_sync.py` (generated-file
  freshness) and `backend/tests/unit/test_ui_mock_parity.py` (inventory and planned markers),
  then `npm run test:visual` in `frontend/`.
- Update docs/11 and docs/12 when behaviour or a design rule changes. Record actual checks
  and any unavailable tooling in the implementation status; never mark an unchecked visual
  gate as passed. A session summary, a commit message or a ticked task alone never establishes
  that a screen matches its mock. Use `/ui-screen` for the workflow.
