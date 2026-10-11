# Plan 016 — Labels and learning from people

| Part | Files |
|---|---|
| Domain | `domain/labels.py` (Label, LabelTask, deterministic ID, merge rule: people win), `domain/categories.py` (load `categories.v1.yaml`, cash-flow class per framework), `domain/learning_policy.py` |
| Writers | `agents/nodes/classify.py`, `agents/nodes/read_pages.py`, `agents/nodes/categorize.py` emit labels with run and span IDs; `services/label_writer.py` batches writes (≤ 500 per batch) |
| Extraction Markdown | `domain/extraction_markdown.py` (pure: page reading → Markdown); written by `read_pages` to `extractions/{docId}/p{n}.md` |
| Examples in prompts | `adapters/firestore_vectors.py` (`labelExamples` vectors, same workspace), `agents/prompts/categorize.md` and `classify.md` get an `{{verified_examples}}` block |
| Decisions | `services/label_service.py` (confirm, correct, bulk, apply to similar → `workspaceRules`), events, month dirty |
| API | `api/labels.py`; `api/documents.py` extraction endpoint; workspace profile `accountingFramework`, `learning` |
| UI | `pages/LabelsPage.tsx`, `widgets/LabelTable/` (responsive table, filters, bulk bar), `widgets/LabelPanel/` (page image, extraction Markdown via `SafeMarkdown`, AI vs final, confirm or correct), `features/decide-label/`; category chip on bank lines opens the same panel |
| Evals | `backend/evals/suites/labels.py` (E-LBL: accuracy vs people, calibration buckets) |
| Later | `services/dataset_export.py` (masking, JSONL, BigQuery load), behind `FEATURE_DATASET_EXPORT` |

Firestore: `orgs/{orgId}/labels`, `orgs/{orgId}/workspaceRules`; indexes in
`contracts/firestore.indexes.json`. Schema versions start at 1 ([`22`](../../22-data-migrations.md)).
