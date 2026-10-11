# ADR-005 — Deterministic checks and risk levels; models read and explain

**Status:** Accepted · **Date:** 2026-10-10 · **Revised by:** [ADR-015](ADR-015-scope-finance-workspace-not-loan-review.md)
(the loan scorecard and credit memo became risk levels and month explanations; the principle stands)

## Context

Whether a month is reconciled, whether a document was edited, and how risky a month is must be
consistent, explainable and robust to manipulation. LLMs are excellent readers and writers but
non-deterministic and can be influenced by document content.

## Decision

All arithmetic, duplicate detection, matching, month figures, money flows, risk levels and state
changes are **pure Python** driven by **versioned policy YAML** (`forensics.v1.yaml`,
`reconciliation.v1.yaml`, `risk.v1.yaml`). Models classify, read pages, propose ledger mappings,
categorize the long tail, give a visual second opinion (P1), write month explanations and answer
questions (P1), always from structured inputs and into Pydantic schemas. A **grounding guard**
verifies every number an explanation or answer states.

## Alternatives considered

| Option | Why not |
|---|---|
| LLM-as-judge for the risk level or for matches | Not reproducible; manipulable via documents; impossible to explain to an auditor |
| Trained anomaly model | No labelled outcomes in a hackathon; fake precision |
| LLM computes totals with tools | Adds failure modes for no benefit; code is cheaper and exact |

## Consequences

- The risk rules are honest: transparent, versioned and tunable on real data later. We say so in the
  pitch.
- Prompt injection can at worst distort an explanation, which the guard catches and a person sees. It
  cannot create a match, change a risk level or resolve a review item.
- More code to write in `domain/`, but it is the easiest code to test.
