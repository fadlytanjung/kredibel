# ADR-002 — Run agents inside Cloud Run, not Agent Runtime

**Status:** Accepted · **Date:** 2026-10-10

## Context

ADK agents can be deployed to Agent Runtime (formerly Agent Engine) or run inside our own service on
Cloud Run/GKE. The competition expects deployment on Cloud Run or Firebase. Our pipeline is tightly
coupled to our domain code, Firestore and Document AI, and is triggered by Cloud Tasks.

## Decision

Run the ADK workflow **inside `kredibel-worker` on Cloud Run** (same image as `kredibel-web`). Use
**Agent Platform Sessions** (a managed Agent Runtime capability) only for the assistant's
conversation memory (P1).

## Alternatives considered

| Option | Why not |
|---|---|
| Deploy the pipeline to Agent Runtime | Splits our code across two runtimes; Cloud Tasks → Agent Runtime invocation adds plumbing; less control over timeouts and concurrency |
| One Cloud Run service for web + worker | Public ingress on the service that runs long jobs; can't size CPU/concurrency differently |
| Cloud Run Jobs | Good for batch, but per-task startup and argument passing are clumsier than an HTTP task handler for per-document and per-month runs |

## Consequences

- One image, two services, `APP_ROLE` selects routers.
- We own scaling knobs (worker concurrency 2, timeout 30 min).
- If the team later wants Agent Runtime, both workflows are already ADK `Workflow`s.
- The Finance Assistant (P1) still uses Agent Platform **Sessions and Memory Bank** as managed services without deploying code to Agent Runtime ([ADR-014](ADR-014-finance-assistant-tools-rag-memory.md)).
