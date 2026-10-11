---
name: submission-check
description: Runs the AI Builder Cup pre-submission verification for Kredibel (live prototype, video, repository, proposal, README results, security checks) and reports what is missing. Use before submitting, after the final deploy, or when asked whether the project is ready to submit.
---

# Pre-submission check

Work through `docs/submission/checklist.md` and report each item as ✅ / ❌ with evidence.

1. **Prototype link:** opens in a logged-out private window; the demo account works; S1–S4 behave as
   in `docs/19-delivery-plan.md` §4 (reconciled months, duplicates held, the edited statement lit,
   the changed supplier account flagged).
2. **Video:** ≤ 3:00, public link (YouTube/Vimeo/Drive) opens logged out; follows
   `docs/submission/demo-script.md`.
3. **Repository:** public (if required), README renders, no secrets (`tools/checks/scan_secrets.py`),
   no real data, licence present.
4. **Proposal:** `docs/submission/proposal.md` final; theme stated; numbers match the latest eval report;
   within any portal character limits (measure them).
5. **README Results:** `tools/checks/readme_results.py` passes.
6. **Security:** cross-workspace test passes; worker returns 403 unauthenticated; CSP present; an
   exact duplicate upload does not change usage; (P1 roles) a viewer cannot resolve review items.
7. **Cloud Run:** both services healthy; required labels (if any) present on both
   (`gcloud run services describe … --format='value(metadata.labels)'`).
8. **Status doc:** `docs/20-implementation-status.md` reflects reality (Deployed/Cut).

Report blockers first, then nice-to-haves.
