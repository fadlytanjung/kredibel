# ADR-008 — Same-origin SPA on Cloud Run with Firebase Auth

**Status:** Accepted · **Date:** 2026-10-10

## Context

We need hosting for a React SPA, an API, and user authentication, using Google services only, with
minimal moving parts. Firebase Hosting rewrites to Cloud Run add a request timeout and an extra
deploy target; uploads of up to 20 MB (the free-trial plan limit) must work.

## Decision

Serve the built SPA **from `kredibel-web` itself** (same origin as `/api`, no CORS). Use **Firebase
Authentication** (email/password + Google) in the browser; the API verifies ID tokens with the
Firebase Admin SDK; org and role are custom claims set by an admin script.

## Alternatives considered

| Option | Why not (for now) |
|---|---|
| Firebase Hosting + rewrite to Cloud Run | Extra deploy target and rewrite limits; useful later for CDN/custom domain |
| Identity Platform with multi-tenancy | More setup than a prototype needs; Firebase Auth is the same family and upgradeable |
| Signed URLs for uploads/downloads | IAM `signBlob` setup and URL leakage risk; streaming through the API is simpler at our file sizes |

## Consequences

- One deploy updates UI and API together.
- The Cloud Run URL must be in Firebase authorized domains; the CSP must allow Firebase endpoints.
- Static assets are served by Uvicorn/FastAPI. That is fine at demo scale; Hosting/CDN is the scale path.
