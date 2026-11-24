# Meet the Builders (Google Gen AI APAC Builder 2026)

> The "Get Featured" submission: if selected, Kredibel goes on the Meet the Builders page with the
> Google Gen AI APAC Builder 2026 badge. The module closes **26 Nov 2026, 01:29 IST**
> (25 Nov 2026, 19:59 UTC; 26 Nov 2026, 02:59 WIB). Rules as published, 23 Nov 2026.

| Field | Rule | Ours |
|---|---|---|
| **Challenge** | Pick from the list | The fraud and financial-risk challenge if it is listed (Kredibel's track in the AI Builder Cup was *BFSI: Intelligent Risk, Fraud & Financial Experiences*) |
| **Demo video** | Google Drive link, "Anyone with the link"; at most 90 s and under 15 MB; **starts with you on camera** (name, where you are from), then the problem, the solution working, who it helps; names the Google AI tools | `kredibel-featured.mp4` in this folder (kept out of git), made by `make video-featured CAMERA=…`; script [`script.md`](script.md) |
| **Google AI tools** | Three bullets, `Tool name: what it does in your project`, at most 1,024 characters | [below](#google-ai-tools-for-the-form) |
| **Social post** | Public, on LinkedIn, YouTube, X, Instagram or Facebook, with **#Meetthebuilders** | Draft [below](#social-post) |
| **Repository** | Consent to publish the GitHub repository | <https://github.com/fadlytanjung/kredibel> (public since October) |

## What is new since the AI Builder Cup

The **loan readiness report** (spec 025, [ADR-028](../../adr/ADR-028-loan-readiness-is-the-owners-check.md)):
before a small business applies for credit, Kredibel says whether its checked books are ready to show
a lender (Ready, Almost ready, Not ready yet) and what to fix first, from six checks computed by code,
with the figures a lender reads first, printed or saved as a PDF. It is the owner's check of the books,
never a credit decision. Live at <https://kredibel.app/readiness> (demo account below).

## The video

1. **Record your intro** (about 10 seconds, landscape, 1080p if the camera allows, face lit from the
   front, a quiet room). Say, in your own words:
   > Hi, I'm Muhammad Fadly Tanjung from *(your city)*, Indonesia. With my team, I built Kredibel.

   If the words differ, change the `camera` sentence in `tools/video/featured/narration.json` so the
   captions match. Save the clip anywhere, e.g. `~/Movies/intro.mov`.
2. **Make the film**: `make video-featured CAMERA=~/Movies/intro.mov`. It voices the narration with
   Google Cloud Text-to-Speech, records the story on production with the demo account (it resets the
   demo account first), puts your clip first with your name tag, and encodes the film under 90 s and
   15 MB (it stops with a message if either is exceeded). Without `CAMERA` the first scene is a
   placeholder card, for a preview. After a new take of the intro alone:
   `make video-featured-cut CAMERA=… CAMERA_FROM=… CAMERA_TO=…` (no new recording; the two seconds
   trim the take). The name tag covers a video call's own name label in the bottom-left corner.

   The take used (24 Nov 2026, a Zoom recording, 640x360, kept out of git):
   `make video-featured-cut CAMERA=docs/submission/meet-the-builders/video1197973444.mp4 CAMERA_FROM=2.9 CAMERA_TO=10.3`
   gives `kredibel-featured.mp4`, 1:16, 13.8 MB: "Hi, my name is Fadly Tanjung. I'm from Indonesia.
   With my team, I built Kredibel."
3. **Upload** `docs/submission/meet-the-builders/kredibel-featured.mp4` to Google Drive, Share ›
   General access › **Anyone with the link** (Viewer), and paste the link in the form. Check the link
   in a private window: it must play without signing in.

The narration after your intro is an AI-generated voice (Google Cloud Text-to-Speech); say so in the
post if the platform asks. All documents in the video are synthetic.

## Google AI tools (for the form)

```
• Gemini on Vertex AI: reads every bank statement, invoice and receipt from the page image and its text, cites where each value is printed so code can check it, and explains each month's fraud risk and next steps in plain words.
• Document AI (Enterprise OCR): turns scanned statements and receipt photos into words with their positions, so every value Gemini reads can be verified on the page before it counts.
• Agent Development Kit (ADK) on Cloud Run: runs each document and month as a traced workflow (read, verify, find copies and edits, reconcile, explain) and feeds the loan readiness report.
```

(about 590 characters)

## Social post

Post from your own account (LinkedIn works best for this audience); attach the video or a screenshot
of the loan readiness page.

```
Meet Kredibel: an AI finance workspace that checks a small business's own books, and now tells the owner whether those books are ready to show a lender.

A small business handles about a hundred documents a month. Checking them by hand takes days, and one edited bank statement can hide fraud. Kredibel reads every page, reconciles every month, and shows the evidence behind every number. The new loan readiness report says what to fix before applying for credit.

Built with Google AI:
• Gemini on Vertex AI reads each page and explains each risk
• Document AI reads scans and receipt photos
• Agent Development Kit runs the workflows on Cloud Run

Try it: https://kredibel.app (demo: demo@kredibel.app / Kredibel-Demo-2026)
Code: https://github.com/fadlytanjung/kredibel

#Meetthebuilders #GoogleCloud #Gemini #BuildWithAI #FinTech #SmallBusiness
```

## Before pressing submit

- [ ] `https://kredibel.app/api/health` answers with the deployed commit; `/readiness` opens for the demo account.
- [ ] The video plays from the Drive link in a private window; at most 1:30; under 15 MB; you are on camera first.
- [ ] The post is public and has #Meetthebuilders; its link pasted.
- [ ] The repository is public.
- [ ] Demo account reset after recording: `make demo-account DEMO_ACCOUNT_EMAIL=demo@kredibel.app DEMO_ACCOUNT_PASSWORD=…`.
