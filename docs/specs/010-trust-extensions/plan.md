# Plan 010 — Trust Extensions

## ① Model Armor

| File | Content |
|---|---|
| `ports/content_shield.py` | `ContentShield.screen_file(bytes, mime) -> ScreeningResult` |
| `adapters/model_armor_shield.py` | `modelarmor_v1.ModelArmorClient` with `api_endpoint=modelarmor.{LOCATION}.rep.googleapis.com`; `sanitize_user_prompt` with a file data item (byte type PDF/PNG/JPEG); map `filter_match_state` and the PI&jailbreak filter result |
| `agents/nodes/doc_nodes.py` | real `screen_document` |
| `adapters/gemini_gateway.py` | quarantine guard: every call carries the `doc_ids` it includes; refuse if any is quarantined |
| `infra/model-armor-template.json` | REST body alternative to the gcloud flags (spike S4) |

## ② Revision diff

`adapters/pdf_inspector.py`: write each earlier revision to `revisions/r{k}.pdf`; extract words with
positions for r1 and final; match words by position (same page, IoU ≥ 0.5); numeric strings that
differ → diff entries. `domain/forensics/structure.py`: M03 CRITICAL when a numeric diff exists.
Evidence viewer: "Original revision" block.

## ③ Run timeline

`widgets/RunTimeline/` reading `GET /analysis-runs/{runId}` (stages, usage); horizontal bars scaled to
total duration; table alternative.

## ④ Visual forensics

`agents/prompts/examine_page.md` (what to look for; untrusted-content framing; return regions as
`box_2d` [ymin, xmin, ymax, xmax] on a 0–1000 scale); `agents/llm/schemas.py` `VisualExamination`;
`domain/bbox.py` conversion; `domain/forensics/visual.py` corroboration logic; real `check_visual`.

## ⑤ Remaining checks

One module per category as in 006/007; enable in `forensics.v1.yaml` as each lands; generator
scenarios S4/S5 from spec 002 Phase 5.

## Constitution check

P4 ✔ (screen before read; quarantine enforced in the gateway) · P6 ✔ (corroboration rule) · P3 ✔
(revision diff as evidence) · P7 ✔ (Model Armor, Gemini) · P9 ✔ (P1 only after cut line)
