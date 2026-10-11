# Tasks 002 — Synthetic Data Generator

## Phase 1 — Setup

- [ ] **T002-01** Create `tools/synthetic/` uv project, CLI entry point, fonts folder (DejaVu Sans + licence).
- [ ] **T002-02** `world.py`, `rng.py`, `model.py` (Decimal money, dataclasses).

## Phase 2 — Data generation (TDD)

- [ ] **T002-03** **TDD** `books.py`: each month satisfies the running-balance equation and continuity (property test over seeds 1–20); every bank row has one ledger cash entry; documents add up. (AC-002-4…6)
- [ ] **T002-04** **TDD** `matching_cases.py`: the six special cases exist; `AUTO` intended matches are unambiguous and `PROPOSED` ones ambiguous under `reconciliation.v1.yaml`. (AC-002-7, AC-002-13)

## Phase 3 — Rendering

- [ ] **T002-05** `render_statement.py` per docs/18 §3.1 with sidecar map, watermark, fixed metadata. (AC-002-3, AC-002-4)
- [ ] **T002-06** [P] `render_invoice.py` (sales + 3 supplier layouts) and `render_receipt.py` (JPEG photo and PDF). (AC-002-3, AC-002-5)
- [ ] **T002-07** [P] `render_ledger.py` CSV and XLSX variant. (AC-002-6)
- [ ] **T002-08** **TDD** determinism: generate twice → identical SHA-256 for all files. (AC-002-2)

## Phase 4 — Tampering, duplicates and scenarios (P0)

- [ ] **T002-09** **TDD** T1: 2 revisions; edited value in Helvetica at the row's coordinates; old string absent; metadata updated. (AC-002-8)
- [ ] **T002-10** **TDD** T7–T11 duplicates: T7 same hash; T8 same rows, new hash; T9 scanned invoice; T10 pHash ≤ 8 and new hash; T11 duplicated ledger row. (AC-002-9)
- [ ] **T002-11** T12 changed supplier account and T13 unpaid invoices. (AC-002-10)
- [ ] **T002-12** `scenarios.py` S1–S5 with upload orders; `truth.py`. (AC-002-1, AC-002-11, AC-002-12)
- [ ] **T002-13** `--scan` variant and the fixtures of docs/18 §3.7. (AC-002-14, AC-002-15)
- [ ] **T002-14** `cli.py`; `make synth` generates S1–S5 × seeds 1–5 and the fixtures; copy S1–S4 seed 1 into `tools/synthetic/out/demo/`.

## Phase 5 — P1

- [ ] **T002-15** T4 hidden white text (S6). (AC-002-16)

## Phase 6 — Close

- [ ] **T002-16** `tools/synthetic/README.md` (how to run, scenarios table); update `docs/20-implementation-status.md`.
