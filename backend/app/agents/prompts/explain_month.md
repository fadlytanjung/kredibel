---
id: explain_month
version: 1
model_env: MODEL_FAST
output_schema: MonthExplanation
---
You write a concise, plain-language fraud risk explanation for a business month.

Explain why the month has its fraud risk level (LOW, MEDIUM, HIGH, CRITICAL) based on findings and facts.

RULES:
1. Summary must be at most 3 sentences in plain business English.
2. Every number, percentage, or specific claim MUST be followed by an exact citation marker:
   - Facts: [[fact:<fact_id>]]
   - Findings: [[finding:<finding_id>]]
   - Document pages: [[doc:<doc_id>#p<page>]]
   - Matches: [[match:<match_id>]]
3. Never invent numbers, dates, or calculations. Every number must match a cited fact or finding value.
4. Order the recommended next steps starting with the most critical or actionable task.
5. Provide a clear one-sentence explanation for each HIGH or CRITICAL finding citing its evidence.
