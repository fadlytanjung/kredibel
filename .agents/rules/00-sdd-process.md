---
trigger: always_on
description: Spec-driven development process for Kredibel. Applies to every change.
---

# Spec-driven development

- Every change implements a task from `docs/specs/NNN-*/tasks.md`. If no task covers the change, propose a
  spec or task update first; do not write untracked code.
- Read the spec's `spec.md` and `plan.md` and the docs they link before writing code.
- Respect task order inside a spec. Tasks marked **TDD** start with a failing test that is run and seen
  to fail for the expected reason.
- Acceptance criteria IDs (`AC-NNN-x`) appear in test names or docstrings so they can be traced.
- When the spec is wrong, ambiguous or contradicts another doc: stop, explain the conflict, and propose
  the doc change. Never silently diverge.
- After finishing a task: tick it (`- [x]`), run `make check`, and commit with
  `feat(NNN): <summary>` and `Tasks: TNNN-xx` in the body.
- Update `docs/20-implementation-status.md` in the same commit when a component's status changes;
  record any deliberate deviation in its "Deviations" section.
- P1 work starts only after the P0 path runs end-to-end on Cloud Run (constitution P9).
- If a change alters what a diagram in `docs/diagrams/` or a Mermaid block shows, update it in the same
  commit. `.drawio.svg` files are edited with the draw.io extension, never by hand.
