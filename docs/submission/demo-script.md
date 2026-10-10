# Demo video script (3:00)

> Record in a logged-out browser at 1440×900, with web and worker set to `min-instances=1`. Pre-run S1
> and S3 so their results are ready; run **S2 live** (or cut the waiting time). Voice-over is written
> to be read at a calm pace (~140 words/minute).

| Time | Shot | Voice-over |
|---|---|---|
| 0:00–0:15 | Title card: **kredibel** · "Every number has a source." Then the case list. | "Small businesses run Southeast Asia, but lenders still judge them from PDFs the borrower controls. Editing one takes minutes. Catching it takes days, if it's caught at all." |
| 0:15–0:30 | New case wizard: **Company** "Sunrise Coffee Roasters" (partnership, one bank account, one beneficial owner), IDR 250 million, 12 months; drag in 6 statements + 10 invoices (Digital badges). Header shows "Free trial". | "Kredibel is an agentic credit analyst. Rina onboards the applicant as a company, enters only what she has, and uploads six months of statements and ten invoices." |
| 0:30–0:55 | Run analysis. Live pipeline: screening, classification, **pages read in parallel** ("Reading page 4 of 18"), verification, forensics, cash flow, memo. | "An ADK workflow on Cloud Run takes over. Gemini reads every page image, and each value is checked against what is really printed in the file. We only trust values both readings agree on, so a misread is never mistaken for fraud, and the second reading costs nothing." |
| 0:55–1:30 | Overview: **DECLINE**, hard stop *Tampered document*. Open the March A01 finding → evidence viewer highlights the row; printed vs expected balance; both readings' values; M04 font; **original revision 1,250,000 → 7,250,000**. | "The March statement was edited. The running balance doesn't add up on the fourteenth. That amount uses a different font from every other number in the column. And the PDF still contains its earlier revision: the credit was originally 1.25 million, not 7.25." |
| 1:30–1:50 | Switch to case S3. Reconciliation tab: invoiced vs matched; 5 unmatched invoices. | "In another application, the statements are genuine, but the revenue isn't. Half the invoices never reached the bank. Kredibel refers the case instead of trusting the paperwork." |
| 1:50–2:00 | Applicant tab: suggestions "Tax ID … (10 invoices)" and "Address …" with evidence chips; accept one; counterparties: six clients, three suppliers. | "Onboarding fills itself in. Kredibel found the tax ID, the address and the client list in the documents, each with the page it came from. Rina accepts with one click." |
| 2:00–2:10 | S6 (if shipped): an invoice flagged **Embedded instructions**; show the hidden text revealed; status Quarantined. | "One invoice even tried to talk to our AI: hidden text telling it to approve. Model Armor caught it before any model read the file." |
| 2:10–2:30 | Memo tab: citation chips; hover a figure → fact popover; click → page. Badge "Figures verified". | "Gemini drafts the credit memo from computed facts only. Every number carries a citation, and a grounding guard checks each one before the analyst sees it." |
| 2:30–2:45 | Decision panel: Approve disabled ("2 critical findings open"); Decline with reason; Activity shows the audited event. | "The decision stays human. Kredibel won't let anyone approve over open critical findings, and every decision is audited." |
| 2:45–3:00 | Architecture slide (one diagram) + Google Cloud logos as text + tagline. | "Built on Google Cloud: ADK, Gemini, Document AI, Model Armor, Cloud Run, Firestore. Kredibel: every number has a source." |

**Fallbacks:** if S6/P1 isn't shipped, extend the S2 evidence segment and the Applicant segment by 5 s each.
If live runs are slow, record the run once and cut to the finished state with a "~2 min later" caption.
