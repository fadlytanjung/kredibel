# ADR-005 — Deterministic scoring; models read and explain

**Status:** Accepted · **Date:** 2026-10-10

## Context

Credit decisions must be consistent, explainable and robust to manipulation. LLMs are excellent
readers and writers but non-deterministic and can be influenced by document content.

## Decision

All arithmetic, metrics, matching, scoring, hard stops and state transitions are **pure Python** driven
by **versioned policy YAML**. Models classify, extract, categorize the long tail, give a visual second
opinion, and write explanations and the memo, always from structured inputs and into Pydantic
schemas. A **grounding guard** verifies every number the memo states.

## Alternatives considered

| Option | Why not |
|---|---|
| LLM-as-judge for the recommendation | Not reproducible; manipulable via documents; hard to defend to a regulator |
| Trained ML scorecard | No outcome data in a hackathon; would be fake precision |
| LLM computes metrics with tools | Adds failure modes for no benefit; code is cheaper and exact |

## Consequences

- The scorecard is honest: illustrative, transparent, calibratable. We say so in the pitch.
- Prompt injection can at worst distort an explanation, which the guard and the analyst then see. It
  cannot change a score or a decision.
- More code to write in `domain/`, but it is the easiest code to test.
