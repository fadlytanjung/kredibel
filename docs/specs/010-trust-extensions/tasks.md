# Tasks 010 — Trust Extensions (P1)

Do the blocks in order; stop at feature freeze.

## ① Model Armor

- [ ] **T010-01** Spike S4: create template; screen S6's invoice as a file; record location and result in docs/02 §6.
- [ ] **T010-02** `ContentShield` port + fake; `ModelArmorShield` adapter.
- [ ] **T010-03** **TDD** `screen_document` node: match → S01 + quarantine + status; error → LOW finding + continue. (AC-010-1, AC-010-2, AC-010-4)
- [ ] **T010-04** **TDD** gateway quarantine guard; S6 scenario asserts zero calls with quarantined content. (AC-010-3)
- [ ] **T010-05** Generate S6 (spec 002 T002-13); scenario test both flag states. (AC-010-5)

## ② Revision recovery

- [ ] **T010-06** **TDD** revision extraction + positional word diff (S2 fixture). (AC-010-6)
- [ ] **T010-07** M03 → CRITICAL on numeric diff; facts before/after. (AC-010-7)
- [ ] **T010-08** Evidence viewer "Original revision" block. (AC-010-7)

## ③ Run timeline

- [ ] **T010-09** RunTimeline widget in Activity with totals. (AC-010-8)

## ④ Visual forensics

- [ ] **T010-10** Spike S5 (box_2d quality) if not done on day 0.
- [ ] **T010-11** `examine_page.md`, `VisualExamination` schema, conversion. (AC-010-9)
- [ ] **T010-12** **TDD** corroboration logic (row match, IoU ≥ 0.3, cap MEDIUM). (AC-010-10)
- [ ] **T010-13** Real `check_visual` behind `FEATURE_VISUAL_FORENSICS`.

## ⑤ Remaining checks

- [ ] **T010-14** **TDD** each remaining check (A03, A05, M05, X02, X03, X04, R03, C03, C04, B02, B03, B05, B06, E04); enable in YAML. (AC-010-12)
- [ ] **T010-15** S4, S5 scenario tests. (AC-010-13)

## Close

- [ ] **T010-16** Update `docs/20-implementation-status.md`; flip feature flags on in `infra/env.*.yaml` for what shipped.
