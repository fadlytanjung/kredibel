---
name: synthetic-scenario
description: Creates or modifies Kredibel synthetic test scenarios (fictional bank statements, invoices, tampering techniques and truth.json) in tools/synthetic. Use when a test, eval or demo needs new documents, a new tamper technique, or updated expected outcomes.
---

# Create or change a synthetic scenario

1. Read `docs/18-synthetic-data.md` (world, templates, techniques, scenarios, truth format).
2. **Fictional only.** Use entities from `kredibel_synth/world.py` or add new clearly fictional ones.
   Every page keeps the "SYNTHETIC — FOR TESTING" watermark and footer.
3. **Data first:** change generators in `transactions.py`/`invoices.py`; renderers only lay out data;
   tamperers (`tamper.py`) modify rendered PDFs and append a `TamperRecord`.
4. **Expected outcomes** go in the scenario builder (`scenarios.py`) and flow into `truth.json`: P0
   codes per document and case, verdicts, hard stops, recommendation, key metrics.
5. **Determinism:** no wall clock or unseeded randomness; fixed metadata and trailer IDs. Run the
   generator twice and compare SHA-256 (the generator test does this).
6. **Invariants:** untampered statements satisfy running balance and continuity; invoices satisfy
   arithmetic (generator tests).
7. Regenerate: `make synth`. If backend scenario tests use recordings for this scenario, re-record
   with `make record SCENARIO=… SEED=…`.
8. Update the scenario table in `docs/18-synthetic-data.md` §5 if a scenario was added or its
   expected outcome changed.
