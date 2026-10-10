---
name: forensic-check
description: Adds or changes a Kredibel forensic, reconciliation, cash-flow or behavioural check (finding code like A01, M04, X01, R01, C01, B01) with policy thresholds, evidence, explanation template and tests. Use when implementing or tuning any check from the risk-engine catalog.
---

# Add or change a check

1. **Catalog.** Confirm the code, rule, severity and priority in `docs/08-risk-engine.md` §2. New
   code → add the row there first (category letter + next number + UPPER_SNAKE name).
2. **Thresholds** go in `contracts/policy/forensics.v1.yaml` (never literals in code). Add the code to
   `enabled` when it is implemented.
3. **Implement** a class satisfying the `Check` protocol in the right module under
   `backend/app/domain/forensics/` (`arithmetic.py`, `structure.py`, `visual.py`,
   `cross_document.py`, `casewide.py`); register it in `registry.py`.
4. **Findings** must include: deterministic `finding_id` (runId|code|anchor), `facts` as decimal
   strings, at least one `EvidenceRef` (doc/page/bbox, transaction, invoice or fact), `detected_by`.
5. **Respect the rules:** arithmetic CRITICAL only on AGREED values (else `E01`); model-based findings
   capped at MEDIUM unless corroborated; integrity verdict logic lives only in `verdict.py`.
6. **Explanation template** for the code in `domain/explain_templates.py` (used when the model
   explainer fails).
7. **Tests (TDD):** below/at/above each threshold; a fixture or generator scenario that triggers it;
   S1 must not trigger it (no false positives on the healthy scenario).
8. **Ground truth:** if a scenario should now raise it, update the generator's expectations
   (`tools/synthetic`) and regenerate; never hand-edit `truth.json`.
9. **Traceability:** update `docs/04-requirements-traceability.md` if a new FR is involved, and
   `docs/20-implementation-status.md`.
