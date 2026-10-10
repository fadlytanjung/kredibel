# Tasks 002 — Synthetic Data Generator

## Phase 1 — Setup

- [ ] **T002-01** Create `tools/synthetic/` uv project, CLI entry point, fonts folder (DejaVu Sans + licence). 
- [ ] **T002-02** `world.py`, `rng.py`, `model.py` (Decimal money, dataclasses).

## Phase 2 — Data generation (TDD)

- [ ] **T002-03** **TDD** `transactions.py`: generated month satisfies the running-balance equation and continuity across months (property test over seeds 1–20). (AC-002-5)
- [ ] **T002-04** **TDD** `invoices.py`: arithmetic holds; S1 payment schedule includes exactly one net-of-tax, one split and one not-due invoice; every other invoice has one exact matching credit. (AC-002-7)

## Phase 3 — Rendering

- [ ] **T002-05** `render_statement.py`: layout per docs/18 §3.1, 2–3 pages, each amount as its own text object, sidecar coordinate map, watermark + footer, fixed metadata, deterministic output. (AC-002-3, AC-002-4, AC-002-6)
- [ ] **T002-06** [P] `render_invoice.py` per docs/18 §3.2. (AC-002-3)
- [ ] **T002-07** **TDD** determinism test: generate twice → identical SHA-256 for all files. (AC-002-2)

## Phase 4 — Tampering & scenarios (P0)

- [ ] **T002-08** **TDD** `tamper.py` T1: 2 revisions; edited value in Helvetica at the row's coordinates; old string absent; metadata updated. (AC-002-8)
- [ ] **T002-09** T3 fake invoices (data-level) with the inflation constraint. (AC-002-9)
- [ ] **T002-10** `scenarios.py` S1, S2, S3; `truth.py` writing expected P0 findings, verdicts, hard stops, recommendation. (AC-002-1, AC-002-10)
- [ ] **T002-11** `cli.py`; `make synth` generates S1–S3 × seeds 1–5; copy S1/S2/S3 seed-1 into `tools/synthetic/out/demo/`.
- [ ] **T002-16** Applicant profiles, `expectedSuggestions` and `expectedCounterparties` in `truth.json`. (AC-002-12)
- [ ] **T002-17** `--scan` variant (rasterize, noise, skew, image-only PDF) and the three fixtures (undeclared account, T6 holder, white-out overlay). (AC-002-13, AC-002-14)

## Phase 5 — P1 scenarios (after P0 cut line)

- [ ] **T002-12** T2 regenerated statement (S5). (AC-002-11)
- [ ] **T002-13** T4 hidden white text (S6). (AC-002-11)
- [ ] **T002-14** T5 stress & gambling profile (S4) and T6 holder mismatch variant. (AC-002-11)
- [ ] **T002-18** S7 related-party inflows. (AC-002-15)

## Phase 6 — Close

- [ ] **T002-15** `tools/synthetic/README.md` (how to run, scenarios table); update `docs/20-implementation-status.md`.
