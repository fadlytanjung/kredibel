# ADR-018 — Firebase Hosting in front of Cloud Run

**Status:** Accepted · **Date:** 2026-10-11 · **Supersedes:** the hosting part of [ADR-008](ADR-008-same-origin-spa-firebase-auth.md)

## Context

ADR-008 served the SPA from `kredibel-web` and named Firebase Hosting as the later scale path. During
spec 001 the team put Firebase Hosting (`kredibel-app.web.app`) in front of Cloud Run, so that the demo
has a stable, readable URL and the static files are served from the CDN edge. ADR-008's worries were
the extra deploy target, the rewrite timeout and 20 MB uploads.

## Decision

**Firebase Hosting serves the SPA** from the same build that is inside the image, and **rewrites
`/api/**`, `/docs` and `/openapi.json` to `kredibel-web`** on Cloud Run. The SPA and the API stay on one
origin, so there is still no CORS. `kredibel-web` keeps serving the SPA too: the `run.app` URL is a
working second front door, and local and container runs need no Hosting.

- Cloud Build copies `/app/static` out of the image it just built and deploys it with
  `firebase deploy --only hosting`, so both front doors always serve the same files.
- `firebase.json` → `hosting.headers` sets the security headers of [`14`](../14-security-and-compliance.md)
  §8 on everything Hosting serves; a unit test (`test_hosting_headers.py`) fails when they differ from
  `core/security_headers.py`. Every response is `no-cache` (Hosting matches header rules on the request path, so this is the catch-all: `index.html` and each public route's own head, spec 020) except hashed `assets/**`, cached for a year, and images and fonts, cached for a day.
- Firebase Auth's authorized domains include the Hosting domains and the `run.app` URL.

## Alternatives considered

| Option | Why not |
|---|---|
| Cloud Run only (ADR-008 as written) | Works, but the demo URL is a long `run.app` name and every asset comes from a Cloud Run instance |
| Hosting for the SPA, API on a separate origin | Needs CORS and a second auth surface |
| Global external load balancer + Cloud CDN | A fixed monthly cost for a prototype |

## Consequences

- The Hosting rewrite has a 60 s timeout. That is the same as `kredibel-web`'s own `--timeout=60`, so
  uploads are not further limited; long work runs on the worker through Cloud Tasks anyway (ADR-006).
- Hosting forwards only the `__session` cookie to Cloud Run. The API uses `Authorization: Bearer`
  headers and no cookies, so nothing is lost.
- The CDN caches a Cloud Run response only when it says `Cache-Control: public`; API responses never do.
- One more deploy step and one more config file (`firebase.json` at the repo root, next to
  `infra/firebase.json`, which deploys Firestore rules and indexes).
- Hosting's free quota covers the demo's traffic ([`21`](../21-cost-analysis.md)).
