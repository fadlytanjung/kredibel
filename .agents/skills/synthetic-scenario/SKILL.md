---
name: synthetic-scenario
description: Creates or modifies Kredibel synthetic test scenarios (fictional statements, invoices, receipts, ledger exports, tamper and duplicate techniques, upload orders and truth.json) in tools/synthetic. Use when a test, eval or demo needs new documents, a new technique, or updated expected outcomes.
---

# Create or change a synthetic scenario

1. Read `docs/18-synthetic-data.md` (world, templates, techniques, scenarios, truth format).
2. **Fictional only.** Use entities from `kredibel_synth/world.py` or add new clearly fictional ones.
   Every page and image keeps the "SYNTHETIC — FOR TESTING" watermark; ledger files carry it in a
   comment row.
3. **Data first:** change `books.py` (bank rows, documents and ledger rows generated together so they
   agree) and `matching_cases.py`; renderers only lay out data; tamperers (`tamper.py`) modify
   rendered files and append a `TamperRecord`.
4. **Expected outcomes** go in the scenario builder (`scenarios.py`) and flow into `truth.json`: per
   document (verdict, risk level, findings, duplicate state), intended matches (`AUTO` or
   `PROPOSED`), per month (state, risk level, minimum auto-match rate, review items by kind, figures),
   suggestions, counterparties and flows. Set the upload order.
5. **Ambiguity is deliberate:** an `AUTO` match must be unambiguous under `reconciliation.v1.yaml`,
   a `PROPOSED` one ambiguous; the generator test checks both.
6. **Determinism:** no wall clock or unseeded randomness; fixed metadata, trailer IDs and image noise
   seeds. Run the generator twice and compare SHA-256 (the generator test does this).
7. **Invariants:** untampered statements satisfy running balance and continuity; documents add up;
   every bank line has its ledger entry unless marked missing.
8. Regenerate: `make synth`. If backend scenario tests use recordings for this scenario, re-record
   with `make record SCENARIO=… SEED=…`.
9. Update the scenario table in `docs/18-synthetic-data.md` §5 if a scenario was added or its expected
   outcome changed.
