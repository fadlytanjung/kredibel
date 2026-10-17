# Submission pack

The five things the challenge requires, where each one is, and what must stay true until judging
ends. Rules as published (copied 17 Oct 2026):

| Requirement | Rule | Ours | Status |
|---|---|---|---|
| **Pitch deck** | On the prescribed template; another format may be disqualified | Content per slide: [`pitch-deck.md`](pitch-deck.md); paste it into the template | Content ready; template to fill |
| **Video demonstration** | 3 to 4 minutes; must clearly show the working solution; longer may be penalised | `demo-video/kredibel-demo.mp4` (2:57, 1920×1080, 15 MB; kept out of git, rebuilt by `make video`) recorded on production with the demo account; script [`demo-video/script.md`](demo-video/script.md) (its times come from the narration; the cut runs a few seconds longer); captions `kredibel-demo.srt`; poster `poster.png` | Rendered for review (the team caps it at 3:00; the rules say 3 to 4 minutes); upload as a public link |
| **Deployed prototype** | A valid, accessible, working link for the whole evaluation; no retries | <https://kredibel-app.web.app> with the demo account `demo@kredibel.app` / `Kredibel-Demo-2026` ([docs/25](../25-demo.md)) | Live |
| **GitHub repository** | Accessible, with the source code and supporting material, for the whole evaluation | <https://github.com/fadlytanjung/kredibel> | Check it is public |
| **Brief description** | What we built, and how we use Firebase, Firestore, Cloud Run and Gemini | [`brief-description.md`](brief-description.md) (short version 820 characters) | Ready |

## Keep the prototype working until judging ends

- **No breaking deploys.** Deploy only from a pushed commit with `make check` green, from a clean
  worktree (`make deploy`); check `https://kredibel-app.web.app/api/health` after each.
- **The demo account is shared.** Anyone can change or reset it; that is by design (docs/25). Reset it
  the evening before judging: `make demo-account DEMO_ACCOUNT_EMAIL=demo@kredibel.app
  DEMO_ACCOUNT_PASSWORD=…`. Never reset the demo template (`org_demo_template`) during judging.
- **Quotas.** The demo workspace is on the free trial (400 pages a month, USD 5 of AI a month); the
  demo company is already read, so browsing costs nothing. An evaluator who uploads their own files
  should sign in with Google and use their own workspace.
- **Sign-in domains.** `kredibel-app.web.app` signs in today. `kredibel.app` signs in only after
  `infra/allow-web-domain.sh kredibel.app www.kredibel.app` (the API key's allowed referrers) and
  `www.kredibel.app` only after it is added in Firebase Hosting ([docs/24](../24-submission-checklist.md) §4).
  Give judges the `web.app` link.
- **Cold starts.** Keep `kredibel-web` at one minimum instance during judging so the first page is
  fast: `gcloud run services update kredibel-web --region=asia-southeast1 --min-instances=1` (and
  back to 0 afterwards; it costs a running instance).

## The video

`tools/video` makes it end to end: `narration.json` (scenes, captions and what the voice says) →
`narrate.py` (ElevenLabs voice "Eric", one clip per sentence, cached) → `frontend/tests/video/demo.spec.ts`
(Playwright on production with the demo account: Chrome's screencast frames, the cursor and captions
drawn in the page, each action at its sentence, page loads cut out) → `edit.py` (ffmpeg: 30 fps, the
narration, dissolves, -16 LUFS; it stops if the film is over 3:00). Run `make video`; it resets the
demo account first. `VIDEO_OWNER_EMAIL=…` adds the Google onboarding scene: `backend/scripts/custom_token.py`
signs that account in (it needs `iam.serviceAccounts.signBlob` on the web service's account), and the
scene ends at the welcome question, so nothing of that account's own workspace is filmed. The title cards are
HTML in `tools/video/cards/`. The ElevenLabs key comes from the environment (`ELEVENLABS_API_KEY`) and
is never written to the repository.

## Older drafts

[`proposal.md`](proposal.md) (long-form proposal), [`demo-walkthrough-guide.md`](demo-walkthrough-guide.md)
(what to click in the prototype, for judges) and [`checklist.md`](checklist.md) (the day-of checklist).
