# Submission checklist

> The day-of checklist. The rules and where each artefact is: [`README.md`](README.md). Target:
> submit before the portal's deadline; record the confirmation.

## Artefacts (the five required)

- [ ] **Pitch deck** on the prescribed template: [`kredibel-pitch-deck.pdf`](kredibel-pitch-deck.pdf)
      from [`kredibel-pitch-deck.pptx`](kredibel-pitch-deck.pptx), aligned with the video; slide 15
      has the three links and their QR codes ([README › The deck](README.md#the-deck)).
- [ ] **Video** 3:00–4:00 (ours: [`demo-video/`](demo-video/)), working functionality on production,
      English voice and captions, uploaded as a public (or unlisted) link that opens without sign-in.
- [ ] **Prototype link** <https://kredibel-app.web.app> opens logged out; the demo sign-in
      (`demo@kredibel.app` / `Kredibel-Demo-2026`) works; `/api/health` answers.
- [ ] **Repository** <https://github.com/fadlytanjung/kredibel> is public; README renders with the
      logo, the live link, the demo account and the video link.
- [ ] **Brief description** pasted from [`brief-description.md`](brief-description.md) (mentions
      Firebase, Firestore, Cloud Run and Gemini); within the field's limit.

## Verification on production (the demo account)

- [ ] Sign in with email and password; a fresh copy asks the welcome question; Skip records a goal.
- [ ] Dashboard (August–October): Matched by Kredibel 95.2%; To review equals the Review page (20).
- [ ] Months: August Critical, September Medium, October High; ≥ 85% matched each month.
- [ ] Risk: August A01/A02/M01–M04 (the evidence viewer lights the edited amount); October X08.
- [ ] Documents: uploading `statement-2026-10.pdf` again says "Not read again and not counted".
- [ ] Transactions: ten rows a page; a cash deposit is "Sales receipts (From its match)".
- [ ] Assistant: "How much money went out in October 2026?" answers IDR 705,933,026.00 with a citation.
- [ ] A second account (Google) sees nothing of the demo workspace.
- [ ] Worker rejects unauthenticated calls (403); no secrets in the repo (`make check` runs the scan).

## Keep it working until judging ends

- [ ] `make check` green on `main`; the deployed version (`/api/health` `version`) is a pushed commit.
- [ ] Demo account reset the evening before judging (`make demo-account …`); the template untouched.
- [ ] `kredibel-web` minimum instances set to 1 during judging (cold starts), back to 0 after:
      `gcloud run services update kredibel-web --region=asia-southeast1 --min-instances=1`.
- [ ] Give judges `https://kredibel.app` (mirror `kredibel-app.web.app`); never `www.kredibel.app` (no DNS).

## After submitting

- [ ] Screenshot of the submission confirmation in the team drive.
- [ ] Freeze `main`; tag `v1.0-submission`.
