---
trigger: glob
globs: backend/**/*.py
description: Python conventions for the Kredibel backend.
---

# Backend Python conventions

- Python 3.12, `uv` only; type-checked with pyright strict; formatted and linted with ruff (line 100).
- `async` for I/O. Wrap sync SDKs (Storage, pikepdf, pdfplumber, pypdfium2) with
  `anyio.to_thread.run_sync`. Prefer async Google clients where available.
- Money: `Decimal` and the `Money` value object. Never `float` for amounts, balances or ratios that
  are stored or compared. Firestore uses integer minor units (`…Minor` fields).
- Time: inject `Clock`; store UTC; document dates are `YYYY-MM-DD` strings.
- IDs: prefixed ULIDs; content-derived IDs per `docs/09-data-model.md` §4. Re-runs upsert, never duplicate.
- Pydantic v2 at every boundary; camelCase aliases for Firestore/JSON (`alias_generator=to_camel`).
- Errors: raise `DomainError` subclasses with a stable `code`; the API renders RFC 9457 problem+json.
- Logging: structlog JSON; bind `case_id`, `run_id`, `doc_id`, `node`. Never log document text,
  descriptions, names, account numbers, prompts with content, or model outputs.
- Firestore writes in chunks of ≤ 400; state changes and their audit event in the same transaction.
- Comments explain why. Files ≤ 400 lines, functions ≤ 50 lines as a guideline.
- Tests: `backend/tests/{unit,integration,scenarios}`; fakes for every port; names state the
  behaviour and the requirement (`test_fr044_…`).
