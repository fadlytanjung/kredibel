# Tasks 008 — Scoring & Credit Memo

## Phase 1 — Scorecard (TDD)

- [ ] **T008-01** **TDD** policy schema for `scorecard.v1.yaml` (invalid weights not summing to 100 fail).
- [ ] **T008-02** **TDD** band evaluation both directions, penalties, floor, `whenMissing`, map components. (AC-008-1)
- [ ] **T008-03** **TDD** hard-stop predicates and recommendation combination (each hard stop; missing metric doesn't fire). (AC-008-2)
- [ ] **T008-04** **TDD** conditions templating with formatted fact values. (AC-008-4)
- [ ] **T008-05** `score_case` node; store scorecard + recommendation (incl. installment figures). (AC-008-5)

## Phase 2 — Grounding guard (TDD)

- [ ] **T008-06** **TDD** marker parser and unknown-citation detection.
- [ ] **T008-07** **TDD** number extraction across formats; ignore dates/years. (AC-008-10)
- [ ] **T008-08** **TDD** matching with display precision; percentages; ambiguous `M`. (AC-008-10)

## Phase 3 — Memo writer

- [ ] **T008-09** `facts_bundle.py` (no document text; masked accounts only). (AC-008-6)
- [ ] **T008-10** `draft_memo.md` prompt + memo writer Agent node + fallback model. (AC-008-6, AC-008-7, AC-008-8, AC-008-9)
- [ ] **T008-11** Guard loop wiring with feedback; UNVERIFIED path. (AC-008-11)

## Phase 4 — Finalize & API

- [ ] **T008-12** `finalize_run` (summary, statuses, usage, event; stale protection). (AC-008-13)
- [ ] **T008-13** `GET /analysis` extended; `GET /memo`. (AC-008-14)
- [ ] **T008-14** Scenario tests: S1/S2/S3 recommendations and hard stops; memos VERIFIED with recordings. (AC-008-3, AC-008-12)

## Phase 5 — Close

- [ ] **T008-15** Update `docs/20-implementation-status.md`.
