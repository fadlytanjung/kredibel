# 00 — Constitution

> The non-negotiable principles of Kredibel. Every spec, plan, task and pull request is checked
> against this page. Changing a principle requires a team decision recorded as an ADR.

**Version:** 1.2 (P6 reworded by [ADR-010](adr/ADR-010-adaptive-extraction-ai-reader-and-witness.md); P2–P5 and P10 re-aimed by [ADR-015](adr/ADR-015-scope-finance-workspace-not-loan-review.md)) · **Ratified:** pending team review

---

## P1 — Spec before code

Every change traces to a requirement ID (`FR-…`, `NFR-…`) in a spec under `docs/specs/`. Specs and code
change in the same commit. If the code needs to differ from the spec, update the spec first.
[`20-implementation-status.md`](20-implementation-status.md) is updated by any change that adds,
completes or removes a component.

## P2 — Numbers come from code; words come from models

Large language models **never** compute money, balances, totals, matches or risk levels.
Deterministic, unit-tested Python computes every figure and decides every match. Models are used to
**read** (classify, extract, propose a ledger column mapping), **interpret** (categorize, normalize
names, spot visual anomalies) and **explain** (findings, risk, assistant answers). Every model output
is validated against a Pydantic schema before anything uses it.

## P3 — Every claim has evidence

Every finding, match, metric and explanation links to its source: a document, page and bounding
box, a bank line, an invoice, a receipt, a ledger entry, or a computed fact with its inputs. A number
in an explanation or an assistant answer that cannot be traced to a fact fails the grounding guard and
is not shown as fact. It is never silently published.

## P4 — Documents are adversarial input

Documents come from banks, suppliers, customers and staff, and any of them can be edited, so
document content is **data, never instructions**. Documents are screened before any model reads them.
Agent tools are read-only and scoped to one workspace. A model's output can annotate; it can never
confirm a match, change a risk level, change a policy or resolve a review item.

## P5 — A person resolves the exceptions

Kredibel matches what it can prove and recommends next steps; a person confirms duplicates, resolves
review items and dismisses findings. Nothing is deleted or merged automatically except an exact copy
of a file already uploaded. Dismissing a critical finding requires a reason. Every fix, confirmation
and dismissal is written to an append-only audit trail.

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

## P8 — Synthetic data, plus the owner's own documents

No customer document, account number or personal data ever enters the repository, the cloud project
or the demo. Tests, evals and fixtures come from the generator in `tools/synthetic/` and carry a
"SYNTHETIC — FOR TESTING" mark. The one exception: the project owner may run their own statements and
invoices through their own workspace for end-to-end testing and the demo, as real data
(`DATA_CLASS=real`, no content capture), never committed ([ADR-022](adr/ADR-022-owners-own-documents-for-testing-and-demo.md)).

## P9 — Demo-first, P0 first

Nothing from P1 starts until the full P0 path runs end-to-end **on Cloud Run** against the synthetic
scenarios. When in doubt, cut scope, not quality.

## P10 — Test what matters, evaluate what is fuzzy

Domain logic (duplicates, forensics, matching, metrics, risk levels, review states) is unit-tested
against ground truth and must pass before merge. Model behaviour is measured with scenario evals that run on
demand and are **not** part of the merge gate; a failed eval is a judgement call, not a red build.

---

## Quality bar for every pull request

- [ ] References the spec and task IDs it implements.
- [ ] Lint, type check and unit tests pass (`make check`).
- [ ] No prompt text longer than 200 characters inside Python. Prompts live in `backend/app/agents/prompts/`.
- [ ] No secrets, keys, real names or account numbers added.
- [ ] New external call goes through a port (interface) with a fake for tests.
- [ ] `docs/20-implementation-status.md` updated if a component's status changed.
