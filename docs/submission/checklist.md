# Submission checklist

> Target: submit **17 Oct 2026, 21:00 UTC+7** (deadline 18 Oct; time zone unconfirmed). Owner: role D.

## Before D7

- [ ] Registration and team formation confirmed on the Hack2skill dashboard (closes **11 Oct**).
- [ ] Official FAQ re-read for: exact deadline and time zone, required portal fields, character
      limits, required Cloud Run labels or hashtags, repository visibility, video length.
- [ ] Every team member meets eligibility (working professional, 21+, JAPAC, not a student).

## Artefacts

- [ ] **Prototype URL** works logged out; demo accounts listed in the submission notes.
- [ ] **Video** ≤ 3:00, public link, follows `demo-script.md`, English, captions on.
- [ ] **Proposal** (`proposal.md`) final; all `⟨…⟩` replaced; numbers match the eval report; under
      portal limits (measure: `python3 -c "print(len(open('brief.txt').read()))"`).
- [ ] **Repository** link works; README renders; docs and code in English.
- [ ] **Theme** stated: Theme 1 — BFSI.

## Verification (run `/submission-check`)

- [ ] S1 → APPROVE/APPROVE_WITH_CONDITIONS; S2 → DECLINE (TAMPERED_DOCUMENT); S3 → REFER.
- [ ] Evidence viewer opens the edited March row with highlights.
- [ ] Analyst cannot approve S2; decline with reason works; event visible.
- [ ] Second org account sees no cases.
- [ ] Worker rejects unauthenticated calls (403).
- [ ] No secrets in the repo or image; `scan_secrets.py` clean.
- [ ] README "Results" passes `readme_results.py`.
- [ ] `min-instances` back to 0 after recording.

## After submitting

- [ ] Screenshot of the submission confirmation in the team drive.
- [ ] Freeze `main`; tag `v1.0-submission`.
- [ ] Social post (if the competition has a Social Choice award) with the video and repo link.
