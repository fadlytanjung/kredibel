# 16 — Infrastructure & Deployment

> One Google Cloud project, one region for state, one container image, two Cloud Run services.
> Everything here is scripted in `infra/bootstrap.sh` (idempotent) and `cloudbuild.yaml`.

---

## 1. Environments

| Env | Where | Notes |
|---|---|---|
| `local` | Laptop | `APP_ROLE=all`, `TASK_QUEUE_MODE=inline`; uses the real dev project's Firestore/GCS/Document AI/Gemini via `gcloud auth application-default login` (simplest), or the Firestore emulator for pure API work |
| `dev` | GCP project `<PROJECT_ID>` | The only cloud environment during the competition; it is also the demo environment |

Demo hygiene: a dedicated org `org_demo` with seeded cases; `scripts/reset_demo.py` resets it.

---

## 2. Google Cloud resources

| Resource | Name | Location |
|---|---|---|
| Artifact Registry (Docker) | `kredibel` | `asia-southeast1` |
| Cloud Run service (public) | `kredibel-web` | `asia-southeast1` |
| Cloud Run service (IAM-only) | `kredibel-worker` | `asia-southeast1` |
| Cloud Tasks queue | `kredibel-analysis` | `asia-southeast1` |
| Firestore (Native, `(default)`) | — | `asia-southeast1` |
| Cloud Storage bucket | `<PROJECT_ID>-kredibel-docs` | `asia-southeast1` |
| Document AI processors | `kredibel-ocr` (Enterprise Document OCR: witness for scanned pages, P0); `kredibel-form` and `kredibel-invoice` (escalation and thorough mode, P1) | `us` |
| Model Armor template (P1) | `kredibel-docs` | `asia-southeast1` (confirm in S4) |
| Agent Platform Sessions resource (P1) | `kredibel-assistant` | `asia-southeast1` or `us-central1` |
| Firebase project | same project | — |
| Service accounts | `kredibel-web`, `kredibel-worker`, `kredibel-tasks-invoker` | — |
| Budget alert | `kredibel` | billing account |

---

## 3. Bootstrap (`infra/bootstrap.sh`)

Prerequisites: `gcloud` authenticated as a project owner, `firebase` CLI, `uv`, `node`.

```bash
export PROJECT_ID=<your-project>  REGION=asia-southeast1
gcloud config set project "$PROJECT_ID"

# 1. APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  firestore.googleapis.com storage.googleapis.com cloudtasks.googleapis.com documentai.googleapis.com \
  aiplatform.googleapis.com modelarmor.googleapis.com iam.googleapis.com iamcredentials.googleapis.com \
  logging.googleapis.com monitoring.googleapis.com cloudtrace.googleapis.com firebase.googleapis.com \
  identitytoolkit.googleapis.com

# 2. Registry, bucket, database, queue
gcloud artifacts repositories create kredibel --repository-format=docker --location="$REGION" || true
gcloud storage buckets create "gs://${PROJECT_ID}-kredibel-docs" --location="$REGION" \
  --uniform-bucket-level-access --public-access-prevention || true
gcloud firestore databases create --location="$REGION" --type=firestore-native || true
gcloud tasks queues create kredibel-analysis --location="$REGION" \
  --max-concurrent-dispatches=4 --max-attempts=3 --min-backoff=30s --max-backoff=300s || true

# 3. Service accounts
for sa in kredibel-web kredibel-worker kredibel-tasks-invoker; do
  gcloud iam service-accounts create "$sa" --display-name="$sa" || true
done
SA() { echo "$1@${PROJECT_ID}.iam.gserviceaccount.com"; }

# 4. IAM (least privilege; see docs/14 §5)
for role in roles/datastore.user roles/logging.logWriter roles/cloudtrace.agent \
            roles/monitoring.metricWriter roles/aiplatform.user; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$(SA kredibel-web)" --role="$role" --condition=None
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$(SA kredibel-worker)" --role="$role" --condition=None
done
for role in roles/documentai.apiUser roles/modelarmor.user; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$(SA kredibel-worker)" --role="$role" --condition=None
done
for sa in kredibel-web kredibel-worker; do
  gcloud storage buckets add-iam-policy-binding "gs://${PROJECT_ID}-kredibel-docs" \
    --member="serviceAccount:$(SA $sa)" --role=roles/storage.objectAdmin
done
# Web sets Firebase custom claims when a workspace is created or an invite accepted (spec 013)
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$(SA kredibel-web)" \
  --role=roles/firebaseauth.admin --condition=None
gcloud tasks queues add-iam-policy-binding kredibel-analysis --location="$REGION" \
  --member="serviceAccount:$(SA kredibel-web)" --role=roles/cloudtasks.enqueuer
gcloud iam service-accounts add-iam-policy-binding "$(SA kredibel-tasks-invoker)" \
  --member="serviceAccount:$(SA kredibel-web)" --role=roles/iam.serviceAccountUser
# run.invoker on kredibel-worker is granted after its first deploy (step 6)
```

```bash
# 5. Document AI processors (us) — prints the env values to copy
uv run --project backend python backend/scripts/create_processors.py --project "$PROJECT_ID" --location us --ocr
# P1 (escalation / thorough mode): add --form --invoice

# 6. After the first deploy of kredibel-worker
gcloud run services add-iam-policy-binding kredibel-worker --region="$REGION" \
  --member="serviceAccount:$(SA kredibel-tasks-invoker)" --role=roles/run.invoker

# 7. Firebase (once)
firebase projects:addfirebase "$PROJECT_ID"          # if not already a Firebase project
firebase apps:create web kredibel-web --project "$PROJECT_ID"
firebase apps:sdkconfig web --project "$PROJECT_ID"   # → VITE_FIREBASE_* (public values)
# Console: Authentication → enable Email/Password and Google; add the Cloud Run URL to authorized domains.
firebase deploy --only firestore --project "$PROJECT_ID"   # rules + indexes from infra/firebase.json

# 8. Model Armor template (P1) — flags to confirm in spike S4
gcloud model-armor templates create kredibel-docs --location="$REGION" \
  --pi-and-jailbreak-filter-settings-enforcement=enabled \
  --pi-and-jailbreak-filter-settings-confidence-level=medium-and-above \
  --malicious-uri-filter-settings-enforcement=enabled

# 9. Demo workspace (free trial to 31 Dec 2026 with demo limits), users and claims (spec 013)
uv run --project backend python backend/scripts/seed_demo_workspace.py --org org_demo --name "Demo Lender" \
  --trial-ends 2026-12-31 --admin admin@demo.kredibel --analyst analyst@demo.kredibel --risk-lead risk@demo.kredibel
```

`create_processors.py` uses the Document AI client with endpoint `us-documentai.googleapis.com`,
creates processors of type `OCR_PROCESSOR` (Enterprise Document OCR) and, with `--form --invoice`,
`FORM_PARSER_PROCESSOR` and `INVOICE_PROCESSOR` (confirm with `fetch_processor_types`), and prints the
processor IDs and the stable version names to use.

`infra/firebase.json` points `firestore.rules` and `firestore.indexes.json` at `../contracts/`.

---

## 4. Cloud Run services

| Setting | `kredibel-web` | `kredibel-worker` |
|---|---|---|
| Image | `asia-southeast1-docker.pkg.dev/<PROJECT_ID>/kredibel/app:<sha>` | same |
| `APP_ROLE` | `web` | `worker` |
| Auth | `--allow-unauthenticated` (the app verifies Firebase tokens) | `--no-allow-unauthenticated` (IAM) |
| Service account | `kredibel-web` | `kredibel-worker` |
| CPU / memory | 1 vCPU / 1 GiB | 2 vCPU / 2 GiB |
| Concurrency | 40 | 2 |
| Timeout | 60 s | 1800 s |
| Min / max instances | 0 / 5 (set min 1 while recording the demo) | 0 / 3 |
| Labels | `app=kredibel,component=web` | `app=kredibel,component=worker` |

```bash
IMAGE=asia-southeast1-docker.pkg.dev/$PROJECT_ID/kredibel/app:$SHA
gcloud run deploy kredibel-worker --image="$IMAGE" --region="$REGION" --no-allow-unauthenticated \
  --service-account="$(SA kredibel-worker)" --cpu=2 --memory=2Gi --concurrency=2 --timeout=1800 \
  --max-instances=3 --labels=app=kredibel,component=worker --env-vars-file=infra/env.worker.yaml
WORKER_URL=$(gcloud run services describe kredibel-worker --region="$REGION" --format='value(status.url)')
gcloud run deploy kredibel-web --image="$IMAGE" --region="$REGION" --allow-unauthenticated \
  --service-account="$(SA kredibel-web)" --cpu=1 --memory=1Gi --concurrency=40 --timeout=60 \
  --max-instances=5 --labels=app=kredibel,component=web --env-vars-file=infra/env.web.yaml \
  --update-env-vars=WORKER_URL="$WORKER_URL"
```

> If the organizers require a specific Cloud Run label for verification, add it to **both** deploy
> commands. `--labels` replaces the whole label set on every deploy.

---

## 5. Container image (`Dockerfile`, outline)

1. **Stage `web`** (`node:22-slim`): `npm ci`, generate API types from `contracts/openapi.yaml`, build
   with the public `VITE_FIREBASE_*` build args → `/fe/dist`.
2. **Stage `app`** (`python:3.12-slim`): install `uv`; `uv sync --frozen --no-dev`; copy
   `backend/app`, `contracts/`, and `/fe/dist` → `/app/static`; run as a non-root user; start
   `uvicorn app.main:app --host 0.0.0.0 --port 8080`.
3. System packages: none required (pikepdf, pdfplumber and pypdfium2 ship wheels).

`kredibel-web` serves `/app/static` with SPA fallback for non-`/api` paths and long-cache headers
for hashed assets.

---

## 6. Configuration (environment variables)

### 6.1 Backend

| Variable | Example | Used by |
|---|---|---|
| `APP_ROLE` | `web` \| `worker` \| `all` | router mounting |
| `APP_VERSION` | git SHA | `/api/health`, logs |
| `GOOGLE_CLOUD_PROJECT` | `<PROJECT_ID>` | all clients |
| `GOOGLE_CLOUD_LOCATION` | `global` | Gemini (ADK, google-genai) |
| `GOOGLE_GENAI_USE_VERTEXAI` | `TRUE` | ADK, google-genai |
| `REGION` | `asia-southeast1` | Tasks, Run URLs |
| `DOCS_BUCKET` | `<PROJECT_ID>-kredibel-docs` | storage |
| `TASK_QUEUE_MODE` | `cloud` \| `inline` | queue adapter |
| `TASKS_QUEUE` / `TASKS_LOCATION` | `kredibel-analysis` / `asia-southeast1` | web |
| `WORKER_URL` | `https://kredibel-worker-…run.app` | web (task target) |
| `TASKS_INVOKER_SA` | `kredibel-tasks-invoker@…` | web (OIDC token on tasks) |
| `DOCAI_LOCATION` | `us` | worker |
| `DOCAI_OCR_PROCESSOR_ID` / `DOCAI_OCR_VERSION` | `abc123…` / Enterprise OCR v2 version name | worker |
| `DOCAI_FORM_PROCESSOR_ID` / `DOCAI_FORM_VERSION` | `ghi789…` / Form Parser v2.0 version name (P1) | worker |
| `DOCAI_INVOICE_PROCESSOR_ID` / `DOCAI_INVOICE_VERSION` | `def456…` / Invoice Parser v2.0 version name (P1) | worker |
| `EXTRACTION_MODE` | `adaptive` (default) \| `thorough` (evals) | worker |
| `EXTRACTION_ESCALATION` | `off` (P0) \| `on` (P1) | worker |
| `ESCALATION_MAX_PAGES_PER_CASE` | `10` (capped by the plan's `escalationPagesPerCase`) | worker |
| `READ_MEDIA_RESOLUTION` | `high` (or `ultra_high` if spike S1 shows it pays off) | worker |
| `PAGE_CONCURRENCY` | `6` | worker |
| `EXTRACTION_CACHE` | `on` (default) \| `ocr_only` (evals: re-read with Gemini, reuse OCR) \| `off` | worker |
| `PREFILL_ON_UPLOAD` | `off` (P1) | web |
| `RUNS_ENABLED` | `true` \| `false` (kill switch: new runs return `503 RUNS_DISABLED`) | web |
| `RUN_QUOTA_PER_ORG_PER_DAY` | `30` (global ceiling above each plan's `runsPerDay`) | web |
| `SIGNUP_MODE` | `open` \| `invite_only` \| `closed` | web |
| `MAX_WORKSPACES` | `15` | web |
| `PLANS_FILE` | `/app/contracts/plans.v1.yaml` | both |
| `MODEL_FAST` / `MODEL_LITE` / `MODEL_REASONING` / `MODEL_REASONING_FALLBACK` | see [`06`](06-agent-design.md) §10 | worker, web |
| `MODEL_ARMOR_LOCATION` / `MODEL_ARMOR_TEMPLATE` | `asia-southeast1` / `kredibel-docs` | worker (P1) |
| `AGENT_SESSIONS_RESOURCE` | `projects/…/locations/…/reasoningEngines/…` | web (assistant, P1) |
| `POLICY_DIR` | `/app/contracts/policy` | both |
| `DOC_CONCURRENCY` / `MEMO_MAX_ATTEMPTS` / `RUN_BUDGET_SECONDS` | `4` / `2` / `600` | worker |
| `FEATURE_MODEL_ARMOR`, `FEATURE_VISUAL_FORENSICS`, `FEATURE_REVISION_DIFF`, `FEATURE_ASSISTANT` | `false` | both |
| `LOG_LEVEL` | `INFO` | both |

`infra/env.web.yaml` and `infra/env.worker.yaml` hold the non-secret values per service. There are no
secrets: all Google access uses the service accounts.

### 6.2 Frontend (build-time, public)

`VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_AUTH_DOMAIN`, `VITE_FIREBASE_PROJECT_ID`,
`VITE_FIREBASE_APP_ID`, `VITE_APP_VERSION`. **`VITE_` values are inlined into the public bundle.**
Never put a server-side value behind a `VITE_` name. Restrict the Firebase web API key to the app's
domains in the console.

---

## 7. Firestore rules: deploy and verify

```bash
firebase deploy --only firestore --project "$PROJECT_ID"
# Verify what is actually released (do not trust the CLI's success message alone):
TOKEN=$(gcloud auth print-access-token)
curl -s -H "Authorization: Bearer $TOKEN" -H "x-goog-user-project: $PROJECT_ID" \
  "https://firebaserules.googleapis.com/v1/projects/$PROJECT_ID/releases"
```

We use the `(default)` database only, which avoids the multi-database rules-deploy pitfall we hit in a
previous project.

---

## 8. CI/CD (`cloudbuild.yaml`)

| Step | Image | Does |
|---|---|---|
| 1 `backend-check` | `python:3.12-slim` + uv | ruff, pyright, import-linter, repo checks, pytest |
| 2 `frontend-check` | `node:22-slim` | `npm ci`, eslint, tsc, vitest |
| 3 `secret-scan` | `python:3.12-slim` | `tools/checks/scan_secrets.py` over the repo |
| 4 `build` | `gcr.io/cloud-builders/docker` | build with `_VITE_FIREBASE_*` substitutions, tag `:$SHORT_SHA` and `:latest` |
| 5 `push` | docker | push to Artifact Registry |
| 6 `deploy-worker` | `gcr.io/google.com/cloudsdktool/cloud-sdk` | `gcloud run deploy kredibel-worker …` |
| 7 `deploy-web` | cloud-sdk | read `WORKER_URL`; `gcloud run deploy kredibel-web …` |
| 8 `smoke` | cloud-sdk | `curl -fsS $WEB_URL/api/health` returns the new `APP_VERSION` |

Triggered manually (`make deploy` → `gcloud builds submit`) during the competition, so a half-finished
push never redeploys the demo by accident.

---

## 9. Runbook

| Situation | Action |
|---|---|
| Roll back | `gcloud run services update-traffic kredibel-web --to-revisions=<prev>=100 --region=$REGION` (same for worker) |
| Run stuck in `PROCESSING` | Check the Cloud Tasks queue and worker logs for `runId`; `scripts/requeue_run.py --case … --run …` re-enqueues (idempotent) |
| `403` from worker in logs | `run.invoker` binding for `kredibel-tasks-invoker` missing (bootstrap step 6) |
| Task creation fails with permission error | `kredibel-web` lacks `iam.serviceAccountUser` on the invoker SA |
| Gemini `404 model not found` | Model ID not available in the project/location; change `MODEL_*`, redeploy |
| Document AI `INVALID_ARGUMENT` on pages | An OCR request with more than 15 pages; check the batching in `docai_ocr` |
| New user stuck on "Finishing setup…" | Custom claims not set: `kredibel-web` lacks `roles/firebaseauth.admin`, or the client didn't refresh its token |
| Sign-ups must stop now | `SIGNUP_MODE=closed` on `kredibel-web` (existing workspaces keep working) |
| Google sign-in popup blocked | Cloud Run URL missing from Firebase authorized domains; CSP `frame-src` |
| Cold start during demo | `gcloud run services update kredibel-web --min-instances=1` (and worker) before recording; set back afterwards |

---

## 10. Cost guardrails

The full analysis, including the database comparison, is in [`21-cost-analysis.md`](21-cost-analysis.md).

- Budget equal to the team's limit, with alerts at 50% / 90% / 100%.
- Firestore `(default)` database only (one database per project gets the free tier); no Cloud SQL.
- Cloud Run scales to zero; Firestore and GCS are pay-per-use.
- Adaptive reading (`EXTRACTION_MODE=adaptive`): one AI reading per page, free text-layer witness, OCR
  only for scans; per-page extraction cache; Flash for the memo in dev.
- Plan limits per workspace (`contracts/plans.v1.yaml`), `SIGNUP_MODE`, `MAX_WORKSPACES`,
  `RUN_QUOTA_PER_ORG_PER_DAY` and the `RUNS_ENABLED` kill switch protect the public demo.
- Artifact Registry cleanup policy keeps the 3 most recent images:
  `gcloud artifacts repositories set-cleanup-policies kredibel --location="$REGION" --policy=infra/ar-cleanup.json`
- Per-run usage is recorded (`runs.usage`) and summarized by `make evals` (E-PERF).
