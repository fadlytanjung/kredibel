# Submission checklist

> Target: submit **17 Oct 2026, 21:00 UTC+7** (deadline 18 Oct; time zone unconfirmed). Owner: role D.

## Before D7

- [ ] Registration and team formation confirmed on the Hack2skill dashboard (closes **11 Oct**).
- [ ] Official FAQ re-read for: exact deadline and time zone, required portal fields, character
      limits, required Cloud Run labels or hashtags, repository visibility, video length.
- [ ] Every team member meets eligibility (working professional, 21+, JAPAC, not a student).

## Artefacts

- [ ] **Prototype URL** works logged out; the demo account is listed in the submission notes.
- [ ] **Video** ≤ 3:00, public link, follows `demo-script.md`, English, captions on.
- [ ] **Proposal** (`proposal.md`) final; all `⟨…⟩` replaced; numbers match the eval report; under
      portal limits (measure: `python3 -c "print(len(open('brief.txt').read()))"`).
- [ ] **Repository** link works; README renders with the logo; docs and code in English.
- [ ] **Theme** stated: Theme 1 — BFSI.

## Verification (run `/submission-check`)

- [ ] S1: months reconciled or with the expected short queue; ≥ 85% matched automatically; LOW risk.
- [ ] S3: exact copy "not read again"; four content duplicates held and confirmable; figures equal S1.
- [ ] S2: March `CRITICAL`; evidence viewer lights the edited value with both readings.
- [ ] S4: May `HIGH` with the supplier's old and new account.
- [ ] Dashboard Sankey opens the bank lines behind a band.
- [ ] A second workspace's account sees nothing of the demo workspace.
- [ ] Worker rejects unauthenticated calls (403).
- [ ] No secrets in the repo or image; `scan_secrets.py` clean.
- [ ] README "Results" passes `readme_results.py`.
- [ ] `min-instances` back to 0 after recording.

## After submitting

- [ ] Screenshot of the submission confirmation in the team drive.
- [ ] Freeze `main`; tag `v1.0-submission`.
- [ ] Social post (if the competition has a Social Choice award) with the video and repo link.
