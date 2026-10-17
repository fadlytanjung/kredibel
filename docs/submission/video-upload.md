# Demo video: YouTube title and description

> Upload `docs/submission/demo-video/kredibel-demo.mp4` (2:57, 1920×1080) under the team leader's
> account as **Public** (the rules ask for a public link). Add `kredibel-demo.srt` as the English
> caption track. Paste the chapters exactly as below (YouTube needs `0:00` first). Tick "Altered or
> synthetic content" in the upload settings: the narration is an AI-generated voice.

## Title (95 characters)

Kredibel: every number has a source | AI Builder Cup 2026 demo (Google Cloud, Gemini, Firebase)

## Description

Kredibel is an AI finance workspace that checks a small business's own books. Upload bank statements, invoices, receipts and your ledger export in any order: Gemini reads every page and cites where each value is printed, code checks it, every month reconciles itself, and what looks wrong (an edited statement, a copied invoice, a supplier paid into a new account) is shown with its evidence. Built for the AI Builder Cup 2026 (Google Cloud JAPAC Hackathon by Hack2skill), BFSI track: Intelligent Risk, Fraud & Financial Experiences.

Measured on the demo company (300 synthetic documents, August to October 2026, read on production): 295 of 310 bank lines reconciled automatically (95.2% / 92.2% / 98.0% by month), every planted case found (an edited statement, a scanned copy, a supplier paid into a new account, unpaid invoices from an unknown supplier), nothing counted twice, every value cited to the page it is printed on.

Try it: https://kredibel.app (mirror: https://kredibel-app.web.app)
Sample books to upload in your own workspace (sign in with Google): https://drive.google.com/drive/folders/1TUpbHZ-nRRoafvzEs4XX1j7rMkM40SfV?usp=sharing
Demo account: demo@kredibel.app / Kredibel-Demo-2026 (shared, synthetic data; reset any time), or sign in with Google for a workspace of your own.
Source code: https://github.com/fadlytanjung/kredibel

Chapters
0:00 A small roaster, a hundred documents a month
0:16 What fraud costs
0:28 Kredibel
0:35 Demo account and what the owner expects
0:51 Dashboard: books against expectations
1:04 Transactions: every bank line explained
1:19 A month reconciles itself
1:27 Risk: the edited statement, the diverted payment
1:43 Late uploads, copies never counted twice
1:59 One review queue
2:07 Labels and traced runs
2:17 Ask the books
2:25 Your own books: sign in with Google
2:39 Built on Google Cloud

Built on Google Cloud: Firebase Hosting and Authentication, Cloud Run (API and Agent Development Kit workflows), Firestore (the books, live updates, vector search), Cloud Tasks, Cloud Storage, Gemini on Vertex AI (Flash, Flash-Lite, embeddings), Document AI OCR, Cloud Trace.

Team Kredibel
Muhammad Fadly Tanjung (team leader)
Ibnu Habibie
Jabbar Ali Panggabean
Muhammad Arisandy Pratama

All documents in the video are synthetic (Sunrise Coffee Roasters is not a real business). Narration: AI-generated voice (Google Cloud Text-to-Speech). Fraud figures: ACFE, Occupational Fraud 2024: A Report to the Nations.

Organised by Hack2skill, sponsored by Google Cloud. @googlecloud @hack2skill

#AIBuilderCup #AIBuilderCup2026 #GoogleCloud #Hack2skill #GenAIAcademy #Gemini #CloudRun #Firebase #Firestore #VertexAI #FinTech #FraudDetection #SmallBusiness #Reconciliation #Kredibel

## Shorter title, if YouTube trims (68 characters)

Kredibel | AI Builder Cup 2026 demo | Google Cloud, Gemini, Firebase

## Notes

- Handles: `@googlecloud` is Google Cloud's YouTube channel; Hack2skill's channel handle may differ
  (search "Hack2skill" on YouTube when uploading and use the handle shown). No official hashtag is
  published on aibuildercup.com; `#AIBuilderCup` and `#AIBuilderCup2026` are the natural ones.
- Keep comments off or moderated: the demo credentials are public by design.
- The silent cut (`kredibel-demo-silent.mp4` + `.srt`) is for a dubbed version; upload it separately
  if a second-language version is made, with the same description and "(Bahasa Indonesia)" in the title.
