---
name: forensic-check
description: Adds or changes a Kredibel check (finding code like D03, A01, M04, X08, R01, B01, C02) with policy thresholds, evidence, next steps, risk mapping and tests. Use when implementing or tuning any check from the risk-engine catalog, including duplicate and month-level checks.
---

# Add or change a check

1. **Catalog.** Confirm the code, rule, severity, scope (`DOCUMENT` or `MONTH`) and priority in
   `docs/08-risk-engine.md` §2. New code → add the row there first (category letter + next number +
   UPPER_SNAKE name).
2. **Thresholds** go in `contracts/policy/forensics.v1.yaml` (or `reconciliation.v1.yaml` for
   matching rules) — never literals in code. Add the code to `enabled` when it is implemented.
3. **Implement** a class satisfying the `Check` protocol in the right module under
   `backend/app/domain/checks/` (`duplicates.py`, `arithmetic.py`, `structure.py`, `extraction.py`,
   `holder.py`, `cross_document.py`, `reconciliation.py`, `behaviour.py`, `visual.py`); register it in
   `registry.py`.
4. **Findings** must include: deterministic `finding_id` (code|anchor), `facts` as decimal strings,
   at least one `EvidenceRef` (document/page/box, bank line, invoice, receipt, ledger entry, match or
   fact), `detected_by`.
5. **Respect the rules:** arithmetic CRITICAL only on AGREED values (else `E01`); model-based findings
   capped at MEDIUM unless corroborated; duplicates **hold** values, never delete; the integrity
   verdict logic lives only in `verdict.py`.
6. **Risk and next steps:** map the code in `contracts/policy/risk.v1.yaml` (level rules if it should
   raise a month) and add its next-step catalog entry and template explanation; the policy loader test
   fails if a code has no next step.
7. **Review item:** if a person must act on it, add or reuse a review item kind in
   `domain/review_items.py` with its allowed actions (docs/08 §7, docs/10 §4).
8. **Tests (TDD):** below/at/above each threshold; a fixture or generator scenario that triggers it;
   S1 must not trigger it (no false positives on the clean half-year).
9. **Ground truth:** if a scenario should now raise it, update the generator's expectations
   (`tools/synthetic`) and regenerate; never hand-edit `truth.json`.
10. **Traceability:** update `docs/04-requirements-traceability.md` if a new FR is involved, and
    `docs/20-implementation-status.md`.
