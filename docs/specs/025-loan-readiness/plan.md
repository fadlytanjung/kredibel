# Plan 025 — Loan readiness report

## Approach

Thinnest slice: one read endpoint, computed on request from what the month runs already stored. No
new collection, no new model call, no data migration.

1. **Policy** `contracts/policy/readiness.v1.yaml`: the period cap, each check's thresholds and how
   many clients to name. Loaded at start-up by `adapters/policy_files.py` (`load_readiness_policy`)
   and validated by the domain parser; a bad file stops start-up like every other policy.
2. **Domain** `backend/app/domain/readiness.py` (pure): `assess_readiness(ReadinessInput, policy)`
   → `Readiness` (level, checks, totals, months, clients, documents). Inputs are plain values: per
   month the statements present and expected, whether it is reconciled, matched and in-scope line
   counts, money in and out, closing balance, negative-balance days, risk level and a verified
   explanation; the cash-flow gaps; the open findings; the open review items; money in per client;
   read documents per type.
3. **Service** `backend/app/services/readiness_service.py`: gathers the inputs from
   `InsightService` (cash flow, month strip, counterparty flow), the month, finding, review-item
   and document repositories, and calls the domain. `InsightService.month_strip()` becomes public
   (the dashboard's months, unchanged).
4. **API** `backend/app/api/readiness.py`: `GET /api/readiness?period=` with the dashboard's
   period pattern; money as decimal strings with the workspace currency. `contracts/openapi.yaml`
   gains the path and the `Readiness` schemas; `make gen-api`.
5. **Frontend**: `entities/readiness` (`useReadiness`), `pages/ReadinessPage.tsx`
   (`ReadinessContent` for the preview), words in `locales/en/readiness.json`, nav item `readiness`
   (group `insight`, icon `book`), preview route `/preview/readiness`. Print styles in
   `design/mocks/assets/kit.css` (`@media print`: no side, top bar, dock or actions).
6. **Mock**: fixture `contracts/design/fixtures/readiness.json`; `readiness()` in
   `tools/design/mocks/screens_more.py`; inventory entry; the shell's Insight group and More sheet
   list it. Parity spec `frontend/tests/visual/readiness.spec.ts`; every shell baseline is recorded
   again for the new menu item.
7. **Plans**: `loan_readiness_report` leaves `comingSoonFeatures`; Plan and usage, its mock and the
   pricing page follow.

## Files

| Area | Files |
|---|---|
| Policy | `contracts/policy/readiness.v1.yaml` |
| Backend | `app/domain/readiness.py`, `app/services/readiness_service.py`, `app/api/readiness.py`, `app/adapters/policy_files.py`, `app/api/deps.py`, `app/main.py`, `app/services/insight_service.py` |
| Tests | `tests/unit/test_readiness.py`, `tests/integration/test_readiness_api.py` |
| Contract | `contracts/openapi.yaml`, `frontend/src/shared/api/schema.d.ts` (generated) |
| Frontend | `src/entities/readiness/*`, `src/pages/ReadinessPage.tsx`, `src/pages/ReadinessPage.test.tsx`, `src/shared/ui/appShellNav.ts`, `src/app/router.tsx`, `src/app/ShellPreview.tsx`, `src/shared/i18n/*` |
| Design | `design/mocks/assets/kit.css`, `tools/design/mocks/{screens_more,shell,inventory,screens}.py`, `contracts/design/fixtures/readiness.json`, `frontend/tests/visual/readiness.spec.ts` |
| Docs | ADR-028, `docs/03` (FR-005, FR-077), `docs/04`, `docs/11`, `docs/20`, README |

## Dependencies

None new.

## Constitution check

- **Numbers come from code**: every figure, check and level is computed in `domain/readiness.py`.
  The only model words are the month explanations the month run already verified (spec 008).
- **Every claim has evidence**: each `WARN`/`FAIL` names its months or findings, with links.
- **Policy, not code**: thresholds in `readiness.v1.yaml`.
- **Not a credit decision**: ADR-028; the page says so; no score, no recommendation to lend.
- **Workspace-scoped, read-only**: the endpoint uses the caller's workspace only and writes nothing.
- **Tokens and words**: kit classes and generated variables only; words in `readiness.json`.

## Risks

- The demo company is `NOT_READY` (August's edited statement is CRITICAL): that is the point of the
  report, and the video shows what to fix first.
- A nav item changes every shell screenshot: the baselines are recorded again in the same change.
