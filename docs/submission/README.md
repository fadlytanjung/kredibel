# Submission pack

The five things the challenge requires, where each one is, and what must stay true until judging
ends. Rules as published (copied 17 Oct 2026):

| Requirement | Rule | Ours | Status |
|---|---|---|---|
| **Pitch deck** | On the prescribed template; another format may be disqualified | [`kredibel-pitch-deck.pdf`](kredibel-pitch-deck.pdf) (16 slides, 1.1 MB) to upload, exported from [`kredibel-pitch-deck.pptx`](kredibel-pitch-deck.pptx): the team's deck on the organiser's template, slide for slide, with the figures and screens of the video (demo company August–October 2026, 95% matched, demo account); content notes in [`pitch-deck.md`](pitch-deck.md) | Final, with the three links and their QR codes on slide 15 |
| **Video demonstration** | 3 to 4 minutes; must clearly show the working solution; longer may be penalised | `demo-video/kredibel-demo.mp4` (2:56, 1920×1080, 15 MB; kept out of git, rebuilt by `make video`) recorded on production with the demo account; script [`demo-video/script.md`](demo-video/script.md) (its times come from the narration; the cut runs a few seconds longer); captions `kredibel-demo.srt`; poster `poster.png`; a silent cut without captions to dub over, `kredibel-demo-silent.mp4` (`make video-silent`), with `kredibel-demo-silent.srt` as its script | Public on YouTube: <https://youtu.be/5UI2NZFmzrk> (the team caps it at 3:00; the rules say 3 to 4 minutes) |
| **Deployed prototype** | A valid, accessible, working link for the whole evaluation; no retries | <https://kredibel.app> (mirror <https://kredibel-app.web.app>) with the demo account `demo@kredibel.app` / `Kredibel-Demo-2026` ([docs/25](../25-demo.md)) | Live |
| **GitHub repository** | Accessible, with the source code and supporting material, for the whole evaluation | <https://github.com/fadlytanjung/kredibel> | Check it is public |
| **Brief description** | What we built, and how we use Firebase, Firestore, Cloud Run and Gemini | [`brief-description.md`](brief-description.md) (short version 820 characters) | Ready |

## The deck

Slide 15 carries the three links with a QR code each; the codes are also in [`qr/`](qr/) (SVG and
PNG, in the deck's ink, with a margin) for the form, the video description or a poster:

| Link | QR code |
|---|---|
| <https://kredibel.app> | [`qr/kredibel-app.svg`](qr/kredibel-app.svg) |
| <https://github.com/fadlytanjung/kredibel> | [`qr/github.svg`](qr/github.svg) |
| <https://youtu.be/5UI2NZFmzrk> (demo video) | [`qr/demo-video.svg`](qr/demo-video.svg) |

After a change to `kredibel-pitch-deck.pptx`, export the PDF again with an English (US) number
format, or the charts print decimal commas: open the deck with
`open -a Keynote kredibel-pitch-deck.pptx --args -AppleLocale en_US`, then File › Export To › PDF,
image quality Better. Keep it under 5 MB.

## Keep the prototype working until judging ends

- **No breaking deploys.** Deploy only from a pushed commit with `make check` green, from a clean
  worktree (`make deploy`); check `https://kredibel-app.web.app/api/health` after each.
- **The demo account is shared.** Anyone can change or reset it; that is by design (docs/25). Reset it
  the evening before judging: `make demo-account DEMO_ACCOUNT_EMAIL=demo@kredibel.app
  DEMO_ACCOUNT_PASSWORD=…`. Never reset the demo template (`org_demo_template`) during judging.
- **Quotas.** The demo workspace is on the free trial (400 pages a month, USD 5 of AI a month); the
  demo company is already read, so browsing costs nothing. An evaluator who uploads files should sign
  in with Google and use their own workspace; the shared Drive folder
  [AI-BUILDER-CUP-2026](https://drive.google.com/drive/folders/1TUpbHZ-nRRoafvzEs4XX1j7rMkM40SfV?usp=sharing) (`demo-aug-oct/pack`, 39 files) holds synthetic sample
  books for that, so judges need not share the demo account.
- **Sign-in domains.** `kredibel.app` and `kredibel-app.web.app` both serve the app and sign in
  (checked 17 Oct 2026: page, `/api/health`, email and Google sign-in). `www.kredibel.app` has no
  DNS record: never hand it out. Give judges `https://kredibel.app`, with `web.app` as the mirror.
- **Cold starts.** Keep `kredibel-web` at one minimum instance during judging so the first page is
  fast: `gcloud run services update kredibel-web --region=asia-southeast1 --min-instances=1` (and
  back to 0 afterwards; it costs a running instance).

## The video

`tools/video` makes it end to end: `narration.json` (scenes, captions and what the voice says) →
`narrate.py` (Google Cloud Text-to-Speech, Chirp 3 HD voice, one clip per sentence, cached) → `frontend/tests/video/demo.spec.ts`
(Playwright on production with the demo account: Chrome's screencast frames, the cursor and captions
drawn in the page, each action at its sentence, page loads cut out) → `edit.py` (ffmpeg: 30 fps, the
narration, dissolves, -16 LUFS; it stops if the film is over 3:00). Run `make video`; it resets the
demo account first. `VIDEO_OWNER_EMAIL=…` adds the Google onboarding scene: `backend/scripts/custom_token.py`
signs that account in (it needs `iam.serviceAccounts.signBlob` on the web service's account), and the
scene ends at the welcome question, so nothing of that account's own workspace is filmed. `make video-silent`
records the same scenes without the caption bar and cuts them without sound, to the same timings, for a
voice-over in another language; its `.srt` carries the lines and when each is said. The title cards are
HTML in `tools/video/cards/`. Text-to-Speech uses Application Default Credentials; no key is written
to the repository.

## Older drafts

[`proposal.md`](proposal.md) (long-form proposal), [`demo-walkthrough-guide.md`](demo-walkthrough-guide.md)
(what to click in the prototype, for judges) and [`checklist.md`](checklist.md) (the day-of checklist).
