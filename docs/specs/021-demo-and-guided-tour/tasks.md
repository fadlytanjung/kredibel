# Tasks 021 — Demo company and guided tour

- [x] **T021-01** **TDD** `domain/demo.py` and `WorkspaceService.create_demo`; `POST /api/workspaces/demo`; `demoAvailable`. (AC-021-1…3) Built 16 Oct 2026 (`test_demo.py`, `test_demo_workspace_api.py`).
- [x] **T021-02** `FirestoreWorkspaceCopier` with an emulator test; discard on failure. (AC-021-1, AC-021-2) Built 16 Oct 2026 (`test_firestore_workspace_copier.py`; files are copied with server-side copies).
- [x] **T021-03** Onboarding demo card, mock and parity. (AC-021-1, AC-021-3) Built 16 Oct 2026 (`onboarding.spec.ts`).
- [x] **T021-04** **TDD** the guided tour: steps, provider, overlay, Take the tour; mock `tour.html` and parity at three widths. (AC-021-4…6) Built 16 Oct 2026 (`features/tour`, `tour.test.ts`, `tour.spec.ts`).
- [x] **T021-05** `make demo-template`, the template in production, `DEMO_TEMPLATE_ORG`; docs/16, docs/18, docs/20. (AC-021-7) Done 16 Oct 2026: `org_demo_template` built (81 documents, 658 labels, 180 runs), `DEMO_TEMPLATE_ORG` in the settings secret; a live check through the deployed API opened a copy in 9.8 s with every collection equal to the template.
- [x] **T021-06** The tour starts by itself for a person who has not seen it: `tourSeenAt` on the member, `tourSeen` on `GET /api/me`, `POST /api/me/tour`. (AC-021-5) Built 16 Oct 2026 (`test_workspace_api.py`, `tour.spec.ts`).
