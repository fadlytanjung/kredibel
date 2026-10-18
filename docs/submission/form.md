# Submission form answers

> What to paste into the AI Builder Cup 2026 submission form (Hack2skill), field by field.
> Checked 17 Oct 2026: the repository is public, the prototype answers, the demo account is reset.
> Deadline on the event site: **18 Oct 2026** (no time zone given; submit early).

| Field | Answer |
|---|---|
| **Challenge** | **BFSI: Intelligent Risk, Fraud & Financial Experiences** (detecting or reducing fraud and risk, automating complex processes) |
| **Prototype link (GCP / Cloud Run)** | `https://kredibel.app` (mirror `https://kredibel-app.web.app`; Firebase Hosting in front of Cloud Run `kredibel-web`; demo sign-in `demo@kredibel.app` / `Kredibel-Demo-2026`, or any Google account with the sample books from [AI-BUILDER-CUP-2026](https://drive.google.com/drive/folders/1TUpbHZ-nRRoafvzEs4XX1j7rMkM40SfV?usp=sharing)) |
| **Deck (PDF, ≤ 5 MB)** | `docs/submission/kredibel-pitch-deck.pdf` (16 slides, 1.1 MB), exported from `kredibel-pitch-deck.pptx`: the team's deck on the organiser's "Submission Template \| AI Builder Cup", slide for slide, with the team details, demo account, production results and the screens of the video. Add the video link on slide 15 and export again before uploading ([README › The deck](README.md#the-deck)) |
| **GitHub repository (public)** | `https://github.com/fadlytanjung/kredibel` |
| **Demo video link (3–4 minutes)** | ⟨public YouTube link, uploaded under the team leader's account; title and description in `video-upload.md`⟩ |
| **Brief description** | the text below |

## Brief description (for the form)

Kredibel is an AI finance workspace that checks a small business's own books. You upload bank
statements, sales and purchase invoices, receipts and the general-ledger export, in any order.
Gemini reads every page from its image and its own text, and code checks that every value is printed
where Gemini says it is. Kredibel holds copies so nothing is counted twice, finds edited PDFs and
payments to a supplier's new bank account, and reconciles each month: on the demo company (300
documents, about 100 a month) 95% of bank lines are matched automatically, to an invoice, a receipt
or the ledger, each with its reason. What it cannot decide goes to one review queue; every month gets a
risk level with the evidence; a finance assistant answers from the books' own figures with citations.

How it uses Google Cloud: **Firebase** Hosting serves the app and routes /api to Cloud Run;
**Firebase Authentication** signs people in (Google, or email for the public demo) and carries each
person's workspace and role as claims. **Firestore** holds the books (documents, bank lines, invoices,
receipts, ledger entries, matches, months, findings, review items, labels, runs, audit trail), streams
progress live to the browser, and its vector search finds the passages the assistant cites.
**Cloud Run** runs two services: `kredibel-web` (API) and `kredibel-worker` (IAM-only), where Agent
Development Kit workflows process each document and each month from Cloud Tasks. **Gemini** on Vertex
AI reads every page and cites the text chunk of each value (Flash), classifies documents and
categorizes bank lines (Flash-Lite), explains each month's risk through a grounding guard, maps new
ledger layouts and powers the assistant; Gemini embeddings index what it searches. Also Document AI
OCR for scans and photos, Cloud Storage, Cloud Trace, Secret Manager and Cloud Build.

(1,860 characters. If the field is shorter, use the first paragraph alone: 788 characters.)

## Team (as registered; emails are on the registration, not here)

- Muhammad Fadly Tanjung (leader)
- Ibnu Habibie
- Jabbar Ali Panggabean
- Muhammad Arisandy Pratama

## Before pressing submit

- [ ] Video uploaded as **public** (or unlisted with the link), under the leader's account; link pasted.
- [ ] Deck PDF under 5 MB attached.
- [ ] Repository public (checked 17 Oct: yes).
- [ ] Prototype answers at `https://kredibel.app/api/health` and `https://kredibel-app.web.app/api/health` (checked 17 Oct: ok, sign-in allowed on both; `www.kredibel.app` has no DNS record, so never hand it out).
- [ ] Demo account reset (`make demo-account …`) and `kredibel-web` kept at one minimum instance during
      evaluation (19 Oct – 6 Nov): `gcloud run services update kredibel-web --region=asia-southeast1 --min-instances=1`.
