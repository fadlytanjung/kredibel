# 00 — Constitution

> The non-negotiable principles of Kredibel. Every spec, plan, task and pull request is checked
> against this page. Changing a principle requires a team decision recorded as an ADR.

**Version:** 1.1 (P6 reworded by [ADR-010](adr/ADR-010-adaptive-extraction-ai-reader-and-witness.md)) · **Ratified:** pending team review

---

## P1 — Spec before code

Every change traces to a requirement ID (`FR-…`, `NFR-…`) in a spec under `docs/specs/`. Specs and code
change in the same commit. If the code needs to differ from the spec, update the spec first.
[`20-implementation-status.md`](20-implementation-status.md) is updated by any change that adds,
completes or removes a component.

## P2 — Numbers come from code; words come from models

Large language models **never** compute money, balances, ratios, scores or decisions. Deterministic,
unit-tested Python computes every figure. Models are used to **read** (classify, extract),
**interpret** (categorize, spot visual anomalies) and **explain** (findings, memo). Every model output
is validated against a Pydantic schema before anything uses it.

## P3 — Every claim has evidence

Every finding, metric and memo statement links to its source: a document, page and bounding box, a
transaction, an invoice, or a computed fact with its inputs. A number in a memo that cannot be traced
to a fact fails the grounding guard and is shown as unverified. It is never silently published.

## P4 — Documents are adversarial input

The borrower controls the documents, so document content is **data, never instructions**. Documents
are screened before any model reads them. Agent tools are read-only and scoped to one case. A model's
output can annotate a case; it can never change a score, a policy or a decision.

## P5 — A human decides

Kredibel recommends; a credit analyst decides. Approving with an open critical finding is blocked.
Overriding the recommendation requires a reason and the right role. Every decision, override and
dismissal is written to an append-only audit trail.

## P6 — Two readings before an accusation

A document is only called **TAMPERED** on deterministic evidence whose values two **independent
readings** agree on: the AI reader (Gemini on the page image) and a witness (the PDF text layer, or
Document AI OCR for scans), or a specialized Document AI parser where one is used. When readings
disagree, the result is **UNVERIFIABLE**, not fraud. A model's visual opinion alone can raise
suspicion, never a verdict.

## P7 — Google Cloud only

Managed services and AI models come from Google Cloud and Firebase: Gemini on Agent Platform,
Document AI, Model Armor, Cloud Run, Cloud Tasks, Firestore, Cloud Storage, Firebase Auth, Cloud
Build, Artifact Registry. Agent orchestration uses ADK. Open-source libraries inside our own containers
are allowed. No third-party AI APIs or SaaS.

## P8 — Synthetic data only

No real customer document, account number or personal data ever enters the repository, the cloud
project or the demo. All test and demo documents come from the generator in `tools/synthetic/` and
carry a "SYNTHETIC — FOR TESTING" mark.

## P9 — Demo-first, P0 first

Nothing from P1 starts until the full P0 path runs end-to-end **on Cloud Run** against the synthetic
scenarios. When in doubt, cut scope, not quality.

## P10 — Test what matters, evaluate what is fuzzy

Domain logic (forensics, metrics, reconciliation, scoring, state machine) is unit-tested against
ground truth and must pass before merge. Model behaviour is measured with scenario evals that run on
demand and are **not** part of the merge gate; a failed eval is a judgement call, not a red build.

---

## Quality bar for every pull request

- [ ] References the spec and task IDs it implements.
- [ ] Lint, type check and unit tests pass (`make check`).
- [ ] No prompt text longer than 200 characters inside Python. Prompts live in `backend/app/agents/prompts/`.
- [ ] No secrets, keys, real names or account numbers added.
- [ ] New external call goes through a port (interface) with a fake for tests.
- [ ] `docs/20-implementation-status.md` updated if a component's status changed.
