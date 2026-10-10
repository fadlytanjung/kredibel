# ADR-006 — Asynchronous runs through Cloud Tasks

**Status:** Accepted · **Date:** 2026-10-10

## Context

A run takes 1–3 minutes, calls rate-limited services (Document AI, Gemini) and must survive
instance restarts. The browser must not hold a long HTTP request.

## Decision

`POST /analysis-runs` writes the run and enqueues a **Cloud Tasks** HTTP task named `run-{runId}`
targeting `kredibel-worker` with an OIDC token. The worker runs the pipeline within the request
(Cloud Run CPU is allocated for its duration). Progress goes to Firestore; the UI listens. Queue
settings cap concurrency (4) and retries (3, backoff 30–300 s). Locally, an `InlineTaskQueue` runs the
same handler in-process.

## Alternatives considered

| Option | Why not |
|---|---|
| Pub/Sub push | No per-message naming for de-duplication; fewer rate controls |
| Cloud Workflows calling our nodes | Splits orchestration between two systems; ADK already orchestrates |
| Background task inside `kredibel-web` | Lost on scale-in; CPU throttled outside requests |
| Server-Sent Events for progress | Long-held connections; Firestore listeners are simpler and survive reloads |

## Consequences

- Every node must be idempotent (Cloud Tasks delivers at least once).
- A stuck run is diagnosable from the queue and the run document; `requeue_run.py` re-enqueues safely.
