# Demo video script (3:00)

> Record in a logged-out browser at 1440×900 (one phone shot at 390×844), with web and worker set to
> `min-instances=1`. The demo workspace already holds S1 (Jan–Jun, reconciled). Upload the S3 and S2
> extras **live**; S4 is pre-loaded in May. Voice-over is written for a calm pace (~140 words/minute).

| Time | Shot | Voice-over |
|---|---|---|
| 0:00–0:12 | Logo and tagline "Every number has a source." Then the dashboard of Sunrise Coffee Roasters. | "Small businesses close their books by hand. Duplicates slip in, PDFs get edited, and a supplier's 'new bank account' can be a fraudster's." |
| 0:12–0:35 | Dashboard: money in and out, month strip (all green), **money-flow Sankey**; click "Suppliers" → the bank lines behind it. | "Kredibel checks your books. Six months of statements, invoices, receipts and the ledger, uploaded in any order. Eighty-seven percent of bank lines matched automatically, and here is where the money went." |
| 0:35–0:55 | Upload sheet: drop February's statement again → "Already uploaded — not read again". Drop a re-scanned invoice and a re-photographed receipt → "Possible copy of …". | "Send the same file twice and it is never read again. A rescanned invoice or a receipt photographed twice is held until you decide, so nothing is counted twice." |
| 0:55–1:20 | Documents: March statement shows **Tampered**. Risk → the finding → **evidence viewer**: the lamp on the edited credit, both readings, the broken balance. | "This March statement was edited. Gemini reads the page image, the PDF's own text layer is a second witness, and both agree on the numbers — so the running balance that no longer adds up is real. A different font in that one amount, and a second revision in the file." |
| 1:20–1:40 | March explanation with citation chips and ordered next steps; label "figures verified". | "The risk level comes from a policy file. Gemini explains it and lists what to do next, and every number it writes is checked against the facts before you see it." |
| 1:40–2:00 | May is **High**: Roastline Equipment Service paid to a new account at another bank; both accounts side by side; two unpaid invoices from an unknown supplier. | "In May a supplier was paid to an account we have never seen for them. That is how payment diversion works, and here it is flagged with both accounts and the invoice." |
| 2:00–2:25 | Phone (390 px): the review queue — confirm the duplicates, pick the right invoice for an ambiguous transfer; "Updating February…" → month turns Reconciled. | "What AI cannot match goes to one short queue. Each item shows the evidence and only the fixes that make sense. Every fix is audited and the month reconciles again." |
| 2:25–2:40 | (P1) Assistant: "How much did we pay Green Valley Farms in March?" → answer with a citation chip and a small chart; or the run graph of one document. | "Ask about your books. Numbers come from tools, never from the model's memory, and every answer shows its source." |
| 2:40–3:00 | Architecture diagram; Google Cloud services as text; tagline. | "Built on Google Cloud: two ADK workflows on Cloud Run, Gemini, Document AI, Firestore and Cloud Tasks. Kredibel: every number has a source." |

**Fallbacks:** if the assistant is not shipped, show the run graph (P1) or extend the review segment.
If live reading is slow, record it once and cut with a "~30 s later" caption.
