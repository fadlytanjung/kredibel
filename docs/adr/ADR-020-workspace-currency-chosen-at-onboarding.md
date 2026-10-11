# ADR-020 — One currency per workspace, chosen at onboarding

**Status:** Accepted · **Date:** 2026-10-12 · **Amends:** PRD assumption A1 ("one currency (IDR) per
workspace"), the out-of-scope line of spec 013

## Context

The prototype assumed every workspace books in Indonesian rupiah. Businesses we want to show keep
their books in Malaysian ringgit, Singapore dollars, Japanese yen or US dollars, and their statements
and invoices are in that currency. Onboarding never asked, so a ringgit business got an IDR workspace.

## Decision

- A workspace has **one currency**, its reporting currency, chosen at onboarding from **IDR, MYR,
  SGD, JPY and USD** (`contracts/openapi.yaml` `Currency`). The form suggests one from the browser's
  time zone (Asia/Kuala_Lumpur → MYR, Asia/Singapore → SGD, Asia/Tokyo → JPY, Indonesian zones → IDR,
  anything else → USD); the person confirms or changes it.
- **It is fixed after onboarding.** Every stored amount, figure, match tolerance and limit message is
  in that currency, so changing it is not a setting: Settings shows it read-only with **Coming soon**,
  and `PATCH /api/workspace` does not accept it. Support can change it on a workspace that has no
  documents with `scripts/set_workspace_currency.py` (server only, like limit overrides); with
  documents the script refuses unless forced, and says what it would leave inconsistent.
- **Money keeps one shape.** Amounts are `Decimal` in Python, decimal strings with two places in JSON,
  and integer hundredths in Firestore (`amountMinor`) for **every** currency, JPY included (whole yen
  are stored ×100). Display follows the currency: `formatMoney` lets `Intl` choose the decimals, so
  JPY shows none.
- **Documents in another currency** than the workspace's (a USD invoice in a MYR workspace) and
  currency conversion are out of scope for now; the reader records each document's currency when it
  reads one (spec 005), and a mismatch becomes a review item rather than a silent conversion.

## Alternatives considered

| Option | Why not |
|---|---|
| Keep IDR only | Real ringgit, dollar and yen books cannot be shown |
| Multi-currency books with FX conversion | Needs rates, dates and rules per document; far beyond the prototype |
| Let the owner change the currency later | Stored amounts and figures would silently change meaning |
| ISO minor-unit exponents (JPY 0, others 2) in Firestore | Two scales in every query and test; hundredths everywhere is simpler and exact |

## Consequences

- One more onboarding field; the default keeps it to one glance for most people.
- Formatters, figures and the explainer take the currency from the workspace, never a literal `IDR`.
- A workspace's country is still `ID` in the prototype; countries are a separate later decision.
