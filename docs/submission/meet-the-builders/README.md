# Meet the Builders (Google Gen AI APAC Builder 2026)

> The "Get Featured" submission: if selected, Kredibel goes on the Meet the Builders page with the
> Google Gen AI APAC Builder 2026 badge. The module closes **26 Nov 2026, 01:29 IST**
> (25 Nov 2026, 19:59 UTC; 26 Nov 2026, 02:59 WIB). Rules as published, 23 Nov 2026.

| Field | Rule | Ours |
|---|---|---|
| **Challenge** | Pick from the list | The fraud and financial-risk challenge if it is listed (Kredibel's track in the AI Builder Cup was *BFSI: Intelligent Risk, Fraud & Financial Experiences*) |
| **Demo video** | Google Drive link, "Anyone with the link"; at most 90 s and under 15 MB; **starts with you on camera** (name, where you are from), then the problem, the solution working, who it helps; names the Google AI tools | <https://drive.google.com/file/d/1k10h-8Ald6meb9llqjBgijMR20kPL3WP/view?usp=sharing> (1:16, 13.8 MB, public; checked signed out 24 Nov 2026). Made by `make video-featured CAMERA=…`; script [`script.md`](script.md), captions [`kredibel-featured.srt`](kredibel-featured.srt) |
| **Google AI tools** | Three bullets, `Tool name: what it does in your project`, at most 1,024 characters | [below](#the-form-field-by-field) |
| **Social post** | Public, on LinkedIn, YouTube, X, Instagram or Facebook, with **#Meetthebuilders** | [The LinkedIn post](#the-linkedin-post) |
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

## The form, field by field

| Field | Paste |
|---|---|
| **Challenges** | The fraud, risk or financial-services option if listed (Kredibel is fintech: fraud and risk in a small business's books) |
| **Demo Video Drive Link** | `https://drive.google.com/file/d/1k10h-8Ald6meb9llqjBgijMR20kPL3WP/view?usp=sharing` |
| **Google AI Tools Used** | the three bullets below (600 characters; the limit is 1,024) |
| **Link to Your Social Media Post** | the LinkedIn post's link, once posted |
| **I consent to the GitHub Repo being published** | Yes (<https://github.com/fadlytanjung/kredibel> is public) |

```
• Gemini on Vertex AI: reads every bank statement, invoice and receipt from the page image and its text, cites where each value is printed so code can check it, and explains each month's fraud risk and next steps in plain words.
• Document AI (Enterprise OCR): turns scanned statements and receipt photos into words with their positions, so every value Gemini reads can be verified on the page before it counts.
• Agent Development Kit (ADK) on Cloud Run: runs each document and month as a traced workflow (read, verify, find copies and edits, reconcile, explain) and feeds the loan readiness report.
```

## The LinkedIn post

Upload the video itself to the post (LinkedIn plays it in the feed, which a Drive link does not):
`kredibel-featured.mp4`, then **Edit › Captions** with [`kredibel-featured.srt`](kredibel-featured.srt) and
**Thumbnail** with [`linkedin-cover.png`](linkedin-cover.png) (1920x1080). Posting without the video, attach
the cover image instead. Make the post **public** (Anyone), then copy its link (… › Copy link to post) for
the form.

```
Meet Kredibel: your books, checked and ready for a lender. 🚀

A small business handles about a hundred documents a month: bank statements, invoices, receipts. Checking them by hand takes days, and one edited bank statement can hide fraud. When the owner applies for a loan, someone has to check it all again.

Kredibel is an AI finance workspace that checks a business's own books:
✅ Gemini reads every page and cites where each value is printed; code checks it before it counts
✅ Copies are caught at once and never counted twice
✅ Every month reconciles itself: 95% of bank lines matched automatically on our demo company
✅ What looks wrong comes with its evidence, like an amount edited in a PDF editor
🆕 The loan readiness report says whether the books are ready to show a lender and what to fix first, then prints as a PDF

Built with Google AI:
• Gemini on Vertex AI reads every page and explains each month's risk
• Document AI reads scans and receipt photos so every value can be verified
• Agent Development Kit runs every document and month as a traced workflow on Cloud Run

▶️ 90-second demo: https://drive.google.com/file/d/1k10h-8Ald6meb9llqjBgijMR20kPL3WP/view?usp=sharing
🌐 Try it: https://kredibel.app (demo account: demo@kredibel.app / Kredibel-Demo-2026)
💻 Code: https://github.com/fadlytanjung/kredibel

Built with my team: Ibnu Habibie, Jabbar Ali Panggabean and Muhammad Arisandy Pratama.

#Meetthebuilders #GoogleCloud #Gemini #GenAI #BuildWithAI #FinTech #SMEs #Indonesia
```

Tag the teammates (type @ and their names) and, if you like, Google Cloud and Hack2skill. All data in the
video and the cover is synthetic (Sunrise Coffee Roasters is not a real business); the narration after the
intro is an AI voice (Google Cloud Text-to-Speech).

## Before pressing submit

- [x] `https://kredibel.app/api/health` answers with the deployed commit (`fd5fb75`, 24 Nov 2026); `/readiness`
      opens for the demo account (live check: welcome question, menu item, report, print width, 390 px).
- [x] The video plays from the Drive link signed out; 1:16; 13.8 MB; you are on camera first, with your
      name and where you are from. (Drive shares it as "Anyone with the link: Commenter"; Viewer is enough.)
- [x] The repository is public.
- [x] The demo account is a fresh copy (24 Nov 2026).
- [ ] The LinkedIn post is public, has #Meetthebuilders, and its link is pasted in the form.
- [ ] Challenge chosen; consent ticked; submitted before **26 Nov 2026, 01:29 IST (02:59 WIB)**.
