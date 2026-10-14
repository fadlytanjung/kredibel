# Plan 018 — Company classifications and profit and loss

## Approach

Implement a pure report over posted ledger rows and explicit account classifications. A separate
policy (`contracts/policy/profit-loss.v1.yaml`) defines P&L lines and subledger families. Report
coverage always says imported entries; completeness of the company's books is not attested.

- `domain/profit_loss.py`: schemas, validation, Decimal aggregation, exclusions and source facts.
- `ports/ledger_repository.py`, `adapters/firestore/ledger_repo.py`: scoped reads without silently
  truncating, transactional classification plus audit. New classification collection v1; ledger
  persistence model v1 with conservative defaults for previously unspecified posting/currency fields.
- `services/profit_loss_service.py`: workspace currency, period, policy, confirmed user decisions.
- `api/profit_loss.py`: GET report, GET accounts/catalog, PUT classification; generated OpenAPI types.
- `services/assistant_service.py`: deterministic P&L request path, scope and citations shared with API.
- `entities/profit-loss`, `widgets/profit-loss`, `pages/ProfitLossPage.tsx`: query, report, account
  classification controls, dashboard integration; assistant links to the same period.
- `tools/design/mocks/screens.py`, shared kit, mock screenshots, stories and visual baselines.
- `tools/checks/mock_sync.py`: regeneration check in `make check`; permanent UI change rule.

## Contracts and persistence

`ledgerEntries` retains existing source fields and adds optional `postingStatus` (default UNKNOWN),
`currency` (default null), `journalId` (default null). Unknown status/currency cannot contribute.
`accountClassifications/{sha256(accountCode)}` stores orgId, accountCode, pnlLine, subledger,
confirmedBy, confirmedAt, schemaVersion=1. No backfill or breaking migration; existing data stays
unclassified. Readers reject unsupported schema versions. Snapshot updated per docs/22 §2.
Existing org-scoped Firestore read/server-only write rules apply; no composite query/index needed.

## Dependencies and limits

No new library, AI call or managed service. Reuse current Firebase/Firestore adapters, auth and kit.
Ledger import remains owned by spec 005, with no claim that its unchecked tasks are done. This
reporting slice can be implemented/tested independently using the existing ledger collection contract.
The current assistant is a service around DocumentReader, not the fully specified ADK/Sessions
platform; this change adds a deterministic read-only P&L path without claiming that platform is built.

## Constitution check

P1 spec first; P2 Decimal/code; P3 source rows/facts; P4 authenticated scope and no model arithmetic;
P5 audited human mappings; P6 no fraud assertions; P7 existing GCP only; P8 synthetic verification;
P9 explicit user-requested P1 continuation, no additional P0 scope; P10 domain/API/UI tests.

## Risks

Incomplete GL imports, direct journals bypassing subledgers, missing accruals, inventory/COGS,
depreciation, tax and opening/closing entries need accounting review. Report includes imported
activity only and names gaps; it never equates payment status with recognition. A subledger family
mapping is a reporting dimension, not proof that control accounts reconcile. Concurrent readers
may see a newly saved classification on their next refresh; past run outputs are untouched.
