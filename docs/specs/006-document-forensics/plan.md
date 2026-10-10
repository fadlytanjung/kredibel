# Plan 006 — Document Forensics

## Modules

| File | Responsibility |
|---|---|
| `domain/policy.py` | load + validate `forensics.v1.yaml` (Pydantic), expose thresholds; checksum recorded on the run |
| `domain/forensics/base.py` | `Check` protocol, `CheckContext` (document, consensus data, pdf facts, words/fonts, policy, run id), `finding_id()` |
| `domain/forensics/registry.py` | registry + `enabled_checks(policy, scope)` |
| `domain/forensics/arithmetic.py` | A01, A02, A04 (A03, A05 later) |
| `domain/forensics/structure.py` | M01, M02, M03 (detect + grade by content-stream change), M04, M06 |
| `domain/forensics/cross_document.py` | X01, X05 |
| `domain/forensics/verdict.py` | verdict + integrity score |
| `adapters/pdf_inspector.py` (extend) | per-revision page content hashes (open the bytes truncated at each `%%EOF`); per-character font names in numeric columns |
| `agents/prompts/explain_findings.md` + `agents/llm/explainer.py` | `finding_explainer` Agent node with `FindingExplanations` output schema |
| `domain/explain_templates.py` | template explanation per code (fallback) |
| `agents/nodes/doc_nodes.py` | real `check_arithmetic`, `check_structure`, `document_verdict` |
| `agents/nodes/case_nodes.py` | real `check_cross_document`, `explain_findings` |
| `adapters/firestore_repo.py` | `upsert_findings` with `severityRank`, `docId` denormalization |

## M04 algorithm

For each page with a text layer: collect characters inside the bounding boxes of numeric cells of the
amount and balance columns (from consensus rows). For each column, compute the font name share across
values; the majority font must cover ≥ `fontAnomaly.majorityShare` of values (with ≥
`minValuesInColumn` values). Any value whose characters use a different font name, or a size differing
by > 0.5 pt, yields M04 anchored to that row.

## M03 grading

`revisions == 1` → no finding. Otherwise, for each later revision, compare the SHA-256 of each page's
decoded content streams with the previous revision: unchanged pages and only `/Annots`/signature
objects added → MEDIUM; any page content changed → HIGH. (Revision text diff → CRITICAL is spec 010.)

## Constitution check

P2 ✔ (pure code) · P3 ✔ (evidence on every finding) · P6 ✔ (AGREED-only rule, corroboration-ready) ·
P10 ✔ (property tests, fixture PDFs, scenario equality with truth)
