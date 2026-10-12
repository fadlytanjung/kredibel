# ADR-024 — Runtime configuration from one Secret Manager secret

**Status:** Accepted · **Date:** 2026-10-12 · **Supersedes:** "`infra/env.web.yaml` and
`infra/env.worker.yaml` hold the non-secret values per service" and the `_VITE_FIREBASE_*` build
substitutions in [`16`](../16-infrastructure-and-deployment.md) §6 and §8

## Context

Production configuration was split three ways: shared settings in `infra/env.*.yaml`, the SPA's
Firebase config as Cloud Build substitutions that `make deploy` filled from a developer's local
`.env`, and defaults in code. `_VITE_FIREBASE_API_KEY` defaults to empty, so a build started any
other way ships a SPA that cannot sign anyone in, and what production runs with depended on whose
laptop started the build. Secret Manager held nothing for Kredibel. The project's other app keeps
its whole env as one secret (`reflect-ai-env`), mounted as a file.

## Decision

- **One secret, `kredibel-env`** (automatic replication, labels `app=kredibel`, `managed-by=cli`).
  Its payload is the production dotenv shared by both services and the SPA build: every shared
  setting plus `VITE_FIREBASE_*`. Server API keys stay out: Gemini and every Google API use the
  service accounts on Vertex AI, so `GEMINI_API_KEY` and `GOOGLE_API_KEY` are local-only.
- **Cloud Run mounts it as a file** at `/secrets/.env` (never under `/app`: a secret mount hides its
  directory) and sets `ENV_FILE=/secrets/.env`; `Settings` reads the file `ENV_FILE` names (default
  `.env`). Only what differs per service is a plain env var, from `infra/env.<role>.yaml`:
  `APP_ROLE`, and `WORKER_URL` on web. Env vars win over the file (pydantic-settings order).
- **Cloud Build reads the same secret** (`availableSecrets`) for the `VITE_` build args and stops
  when `VITE_FIREBASE_API_KEY` is empty.
- **Editing:** `infra/kredibel-env.example` is the committed template. The real payload is edited
  locally as `.env.production` (gitignored) and pushed with `make env-push`, which refuses
  per-service and local-only keys, adds a version, and compares SHA-256 without printing values.
  `make env-pull` and `make env-keys` read it back. A new version reaches the services on their
  next revision (`make deploy`).
- **Access:** `roles/secretmanager.secretAccessor` on the secret for `kredibel-web`,
  `kredibel-worker` and the build service account (`infra/bootstrap.sh`).

## Alternatives considered

| Option | Why not |
|---|---|
| Keep `infra/env.*.yaml` and build substitutions | The build depends on a developer's `.env`; an empty Firebase key ships silently |
| One secret per key (`--set-secrets=KEY=secret:latest`) | Dozens of secrets to keep in step; not how this project's other app works |
| Expand the file into `--set-env-vars` at deploy | Writes every value into the service config and shell history |

## Consequences

- Configuration changes no longer appear in git diffs. The template must stay in step with
  `Settings` (same keys), and Secret Manager keeps every version for rollback (re-add an older
  payload as a new version).
- The `VITE_` values are public once built into the bundle; they go through the secret so the build
  does not depend on a laptop, not because they are secret.
- Cost: a few active versions and one access per instance start and per build, cents a month
  ([`21`](../21-cost-analysis.md)).
