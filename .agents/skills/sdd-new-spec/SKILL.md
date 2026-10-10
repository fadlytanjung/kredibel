---
name: sdd-new-spec
description: Creates a new Kredibel feature spec folder (spec.md, plan.md, tasks.md) from the template, wired into requirements traceability and the specs index. Use when a new feature, change request or scope addition needs to be specified before coding.
---

# Create a new spec

1. **Clarify the need** in one paragraph: who, what, why, priority (P0/P1/P2). If it changes P0 scope
   after the docs were locked, flag it as a scope change for the team.
2. **Number it**: next free `NNN` in `docs/specs/`. Folder `docs/specs/NNN-short-name/`.
3. **Requirements**: add or reuse `FR-…`/`NFR-…` in `docs/03-prd.md` §7–§8.
4. **spec.md** from the template in `docs/specs/README.md`: summary, user stories, acceptance criteria
   `AC-NNN-x` in Given/When/Then, out of scope, edge cases. No implementation details.
5. **plan.md**: approach, files to create/change (paths per `docs/13` §1), contract changes
   (`contracts/openapi.yaml`, data model, policy YAML), constitution check P1–P10, risks.
6. **tasks.md**: ordered, small tasks `TNNN-xx`, test-first where logic is involved, each referencing
   ACs; a final task to update `docs/20-implementation-status.md`.
7. **Wire it in**: add the row to `docs/specs/README.md` (index + dependency graph),
   `docs/04-requirements-traceability.md`, and a "Specified" row in `docs/20-implementation-status.md`.
8. If the feature makes a significant decision, add an ADR in `docs/adr/`.
