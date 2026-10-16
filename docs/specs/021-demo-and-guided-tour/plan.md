# Plan 021 — Demo company and guided tour

## Backend

- `Settings.demo_template_org` (`DEMO_TEMPLATE_ORG`, empty: no demo).
- `domain/demo.py` (pure): the collections that are not copied, the workspace fields set by the new
  workspace, and `rewrite(value, replace)` that swaps the template's workspace ID and people in every
  string, at any depth.
- `ports/workspace_copier.py`: `copy_records(source, target, replace)`,
  `copy_workspace_fields(source, target, replace)`, `discard(target)`.
- `adapters/firestore/workspace_copier.py`: streams every collection under `orgs/{source}` and
  `orgPrivate/{source}` and writes the rewritten documents in batches of 400; copies every object
  under `orgs/{source}/` in the documents bucket with server-side copies, 16 at a time; `discard`
  deletes both.
- `WorkspaceService.create_demo(principal)`: the checks of `create`, copy the records, create the
  workspace (the same transaction as `create`, so the limit and the one-workspace rule hold), merge
  the template's other workspace fields (ledger mappings), set the claims; on any failure discard.
- `POST /api/workspaces/demo`; `demoAvailable` on `GET /api/me`.
- `make demo-template`: `seed_demo_workspace` then `upload_demo_books` on the books from
  `kredibel-synth demo --shift-months 3`.

## Frontend

- Onboarding: a demo card above the form when `demoAvailable`; `useCreateDemoWorkspace` posts and
  refreshes the session like `useCreateWorkspace`, then opens `/dashboard?tour=1`.
- `features/tour`: the steps (route, the part to highlight, words, owner only), `TourProvider` (start,
  stop, the step, "seen" per person in this browser), `TourOverlay` (a spotlight cut out of a scrim
  around the part's box, the card beside it or at the bottom on phones, focus kept in the card).
- The top bar's **Take the tour** button (`onTour` from the router, like `onUpload`).
- Mocks: `onboarding.html` with the demo card; `tour.html`, the dashboard with the tour on its second
  step. Parity: `onboarding.spec.ts`, `tour.spec.ts`.

## Dependencies

No new package: the spotlight is drawn with the kit's tokens.
