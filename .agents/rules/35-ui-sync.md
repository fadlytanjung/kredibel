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
  Do not edit generated HTML or `frontend/src/app/styles/kit.css` directly.
- Run `make tokens mocks`; inspect affected screenshots at 390/834/1440 px and check
  360/1600 bounds. Update stories and Playwright baselines with the implementation.
- Run `make check`, including `tools/checks/mock_sync.py`. Generated-file freshness is
  necessary; screenshot inspection establishes visual parity.
- Update docs/11 and docs/12 when behaviour or a design rule changes. Record actual checks
  and any unavailable tooling in the implementation status; never mark an unchecked visual
  gate as passed. Use `/ui-screen` for the workflow.
