# Tasks 006 — Document Forensics

## Phase 1 — Framework

- [ ] **T006-01** **TDD** `domain/policy.py` loads `forensics.v1.yaml` and `scorecard.v1.yaml`; invalid files fail at startup.
- [ ] **T006-02** `Check` protocol, `CheckContext`, registry, deterministic `finding_id`. (AC-006-14)

## Phase 2 — Checks (TDD each)

- [ ] **T006-03** **TDD** A01 incl. AGREED-only rule (property test with hypothesis: consistent → none; one edited credit → exactly one at that row). (AC-006-1, AC-006-3)
- [ ] **T006-04** **TDD** A02. (AC-006-2)
- [ ] **T006-05** **TDD** A04 with an invoice fixture. (AC-006-4)
- [ ] **T006-06** **TDD** M01, M02 against metadata fixtures. (AC-006-5, AC-006-6)
- [ ] **T006-07** Extend `pdf_inspector` with per-revision page content hashes; **TDD** M03 grading (signature-only fixture → MEDIUM; S2 → HIGH). (AC-006-5, AC-006-7)
- [ ] **T006-08** Extend `pdf_inspector` with per-character fonts; **TDD** M04 on S2 and none on S1. (AC-006-5, AC-006-6)
- [ ] **T006-09** **TDD** M06 and skipping M04 on image-only pages. (AC-006-8)
- [ ] **T006-10** **TDD** X01 (fixture) and X05. (AC-006-9, AC-006-10)
- [ ] **T006-11** **TDD** verdict + score per docs/08 §3. (AC-006-11)

## Phase 3 — Explanations

- [ ] **T006-12** Template explanations for every P0 code.
- [ ] **T006-13** `explain_findings.md` prompt + explainer Agent node; number check against facts; fallback to template. (AC-006-13)

## Phase 4 — Nodes & persistence

- [ ] **T006-14** Real nodes `check_arithmetic`, `check_structure`, `document_verdict`, `check_cross_document`, `explain_findings`; findings upsert with `severityRank`. (AC-006-12)
- [ ] **T006-15** Scenario test: S1–S3 finding codes per document equal truth; S2 March `TAMPERED`. (AC-006-15)

## Phase 5 — Close

- [ ] **T006-16** Update `docs/20-implementation-status.md`.
