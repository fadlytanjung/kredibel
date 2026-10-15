# Plan 019 — Current UI and mock parity

- Audit the router, pages/widgets and local Gemini continuation against tasks and status.
- Maintain a screen inventory beside the mock generator; show route and implemented/design-only
  status in the mock index. Preserve future designs without presenting them as current UI.
- Update `tools/design/mocks/screens.py` and dedicated screen modules, shared kit, docs/11 and
  docs/12. Preserve the established tokens and visual language. P&L correction is spec 018 T018-07.
- Refresh assistant strings/accessibility and dev-only preview routes for API-backed screen tests.
- Add Playwright parity assertions for principal sections/controls, state screenshots and axe.
  Existing unit/integration tests validate behavior. Compare real DOMs, not source-file timestamps.
- Update the always-on UI-sync rule to require explicit parity evidence and an inventory entry.
- Refresh `docs/20-implementation-status.md` and reopen demonstrably incomplete tasks, with reasons.

No dependency, API, persistence or policy changes. Local previews and fixtures are development-only.
Tests intercept all workspace APIs; no real accounts or services. `make check` remains the full gate.

## Constitution check

P1 spec before edits; P2 code-backed numbers; P3 evidence controls retained; P4 no new model/tool
permissions; P5 human actions preserved; P6 uncertainty states explicit; P7 existing stack; P8 only
synthetic fixtures; P9 existing feature maintenance; P10 browser parity, keyboard, axe and unit gates.

## Risks

Mock freshness alone does not prove parity. Semantic browser checks detect content/layout drift but
screenshots still require review. Future designs may legitimately be richer than current screens;
the inventory must say so. Historical deployed labels need deployment evidence before being changed.
