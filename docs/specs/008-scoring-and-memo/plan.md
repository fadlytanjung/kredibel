# Plan 008 — Scoring & Credit Memo

## Modules

| File | Responsibility |
|---|---|
| `domain/policy.py` (extend) | scorecard schema: components, bands, maps, penalties, grades, hard-stop predicates, conditions |
| `domain/scorecard.py` | `score(metrics, verdicts, findings, policy) -> Scorecard`; band evaluation (`higher_is_better` / `lower_is_better`), penalties, `whenMissing`, hard stops, recommendation combination, conditions templating |
| `domain/facts_bundle.py` | assemble the memo input from case, facts, findings (IDs, codes, titles, severity, doc/page refs), scorecard |
| `domain/grounding.py` | marker parser; number extractor (`IDR`, thousands separators, `million`/`billion`, `x`, `%`); sentence splitter; matcher with display-precision rounding; result model |
| `agents/prompts/draft_memo.md` | section structure, citation rules, tone rules, "use only facts", guard feedback slot |
| `agents/llm/memo_writer.py` | Agent node with `CreditMemoDraft` output schema; fallback model handling |
| `agents/nodes/case_nodes.py` | real `score_case`, `draft_memo`, `grounding_guard`, `finalize_run` |
| `api/memo.py` | `GET /memo` |

## Grounding guard details

1. Split section text into sentences (period/newline, ignoring decimals and abbreviations).
2. Collect markers per sentence; unknown marker → problem `UNKNOWN_CITATION`.
3. Extract numbers; ignore dates, day counts of the form "14 Mar", years, section numbers, and
   numbers inside markers.
4. For each number, find a cited `fact:` in the sentence whose value, rendered at the number's
   precision and unit, equals it. Percentages compare against ratio × 100. Accepted suffixes:
   `million` (10⁶) and `billion` (10⁹). Abbreviations (`K`, `M`, `B`, `mn`, `bn`) are rejected as
   ambiguous; the prompt asks for full numbers or the words "million"/"billion".
5. Number without a matching cited fact → problem `UNGROUNDED_NUMBER`.

## Constitution check

P2 ✔ (scores in code; memo can't change them) · P3 ✔ (citations + guard) · P5 ✔ (recommendation
only) · P10 ✔ (scorecard boundary tests; guard unit tests; memo quality in evals)
