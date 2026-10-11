# Plan 015 — Trust Extensions (P1)

| Story | Files |
|---|---|
| Model Armor | `adapters/model_armor_shield.py`, `screen_document` node, gateway quarantine check, `infra/model-armor-template.json`; spike S4 (regional endpoint, file items) |
| Visual forensics | `agents/prompts/examine_page.md`, `VisualExamination` schema, corroboration in `domain/checks/visual.py` |
| Revision diff | `adapters/pdf_inspector.py` earliest-revision extraction; `domain/checks/structure.py` diff |
| Run graph | `widgets/RunGraph/` (static layouts per workflow, fan-out stacking), `entities/run/useRunLive.ts` |
| Sign-off | `services/month_service.py` sign-off and reopen; lock checks in document, review and match services |
| Exports | `api/exports.py`, CSV writer with injection escaping |
| Split and upload | `services/document_service.py` split option; parts linked to the original |

Each story is merged only with its flag off by default and its own tests.
