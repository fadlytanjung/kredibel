# Plan 008 — Fraud Risk and Explanations

## Backend

| File | Content |
|---|---|
| `domain/risk.py` | document and month levels, score, reasons from `risk.v1.yaml` |
| `domain/next_steps.py` | catalog lookup and default order |
| `domain/grounding.py` | marker parsing, number normalization (IDR, separators, "million"), checks |
| `agents/prompts/explain_month.md` | explainer prompt; `MonthExplanation` schema |
| `agents/nodes/month_nodes.py` | `score_risk`, `explain_month` (hash skip, retry, template fallback) |
| `services/finding_service.py` | acknowledge, dismiss with reason, event, mark month dirty |
| `api/findings.py` | routes of [`docs/10`](../../10-api-contract.md) §2.6 |

## Frontend

| File | Content |
|---|---|
| `pages/RiskPage.tsx` | grouped list with filters; month levels |
| `widgets/EvidenceViewer/` | page viewer with lamp highlight, magnifier crop on compact, readings, calculation |
| `widgets/Explanation.tsx` | summary with citation chips and the grounding label |
| `shared/ui/SeverityBadge.tsx` | colour + icon + text |

## Constitution check

P2 ✔ (levels by rules; the model only phrases) · P3 ✔ (evidence and citations) · P5 ✔ (a person
acknowledges or dismisses) · P6 ✔
