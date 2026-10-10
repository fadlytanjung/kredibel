---
trigger: model_decision
description: Testing and evaluation rules. Read when writing or changing tests, recordings, or evals.
---

# Testing and evaluation

- Gates (`make check`): unit, integration and scenario tests, frontend tests, lint, types, layer
  contracts, repo checks. They never call real Google services.
- Scenario tests replay recorded Gemini page readings, OCR and (P1) parser outputs per page from
  `backend/tests/scenarios/recordings/`; the text-layer witness runs locally. A missing recording fails
  loudly; re-record with `make record` after prompt or processor changes.
- Entitlement tests cover each limit at, below and above the boundary, with an injected clock.
- Expected values come from the generator's `truth.json`; do not hand-write expected numbers.
- Property tests (hypothesis) for arithmetic and consensus invariants.
- Domain coverage ≥ 90%, services ≥ 80%.
- Evals (`make evals`) call real models, run on demand, and are never part of `make check` or Cloud
  Build. README and proposal numbers come only from the latest eval report.
