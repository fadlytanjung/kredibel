---
name: sdd-implement-task
description: Implements the next unchecked task (or a named task) of a Kredibel spec using test-first development, then verifies, ticks and commits it. Use when asked to implement, continue, build or "do the next task" of a spec such as 005 or T005-07.
---

# Implement a spec task

## Inputs

A spec number (`005`) or a task ID (`T005-07`). If neither is given, use the lowest-numbered spec in
`docs/specs/README.md` that has unchecked tasks and whose dependencies are done in
`docs/20-implementation-status.md`.

## Steps

1. **Load context.** Read `AGENTS.md`, `docs/00-constitution.md`, the spec's `spec.md`, `plan.md`,
   `tasks.md`, and every doc section they link for this task.
2. **Pick the task.** The first unchecked task in order (or the named one). Note the acceptance
   criteria it serves.
3. **Check preconditions.** Earlier tasks of the spec are ticked; dependencies exist in code. If not,
   stop and report what's missing.
4. **Test first (TDD tasks).** Write the test(s) named after the behaviour and AC
   (`test_ac005_9_conflicting_amount_is_marked_conflict`). Run them; confirm they fail for the
   expected reason.
5. **Implement** the smallest change that makes the tests pass, following `plan.md` file locations
   and `docs/13` patterns. New external calls go through a port with a fake.
6. **Verify.** Run `make check`. Fix until green. For UI tasks, also run the dev server and check the
   screen states (loading, empty, error, success).
7. **Tick** the task in `tasks.md` (`- [x]`).
8. **Docs.** If behaviour or contracts changed, update the relevant doc in the same change. If a
   component's status changed, update `docs/20-implementation-status.md`.
9. **Commit** `feat(NNN): <summary>` with `Tasks: TNNN-xx` and `AC: AC-NNN-x, …` in the body.

## Stop and ask when

- The spec contradicts another doc or the installed library's API.
- A task would require a new managed service or a third-party API.
- A test can only pass by weakening a guard (auth, isolation, decision rules, corroboration rule).
