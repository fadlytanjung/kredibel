# 16 — Infrastructure & Deployment

> One Google Cloud project, one region for state, one container image, two Cloud Run services.
> Everything here is scripted in `infra/bootstrap.sh` (idempotent) and `cloudbuild.yaml`.

---

## 1. Environments

| Env | Where | Notes |
|---|---|---|
| `local` | Laptop | `APP_ROLE=all`, `TASK_QUEUE_MODE=inline`; uses the real dev project's Firestore/GCS/Document AI/Gemini via `gcloud auth application-default login` (simplest), or the Firestore emulator for pure API work |
| `dev` | GCP project `<PROJECT_ID>` | The only cloud environment during the competition; it is also the demo environment |

Demo hygiene: a dedicated workspace `org_demo` (Sunrise Coffee Roasters) seeded with scenario S1 and
the S2–S4 extras ready to upload live; `scripts/reset_demo.py` resets it.

---

## 2. Google Cloud resources

| Resource | Name | Location |
|---|---|---|
| Artifact Registry (Docker) | `kredibel` | `asia-southeast1` |
| Cloud Run service (public) | `kredibel-web` | `asia-southeast1` |
| Cloud Run service (IAM-only) | `kredibel-worker` | `asia-southeast1` |
| Cloud Tasks queues | `kredibel-documents` (one task per upload), `kredibel-months` (one task per month and generation) | `asia-southeast1` |
| Firestore (Native, database `kredibel`, [ADR-021](adr/ADR-021-kredibel-firestore-database.md)) | — | `asia-southeast1` |
| Cloud Storage bucket | `<PROJECT_ID>-kredibel-docs` (object versioning on, noncurrent kept 7 days) | `asia-southeast1` |
| Cloud Storage bucket (backups) | `<PROJECT_ID>-kredibel-backups` (Firestore exports before migrations; deleted after 30 days) | `asia-southeast1` |
| Firestore protection | point-in-time recovery (7 days), delete protection and a daily backup schedule (7-day retention) on `kredibel` | `asia-southeast1` |
| Cloud Run job | `kredibel-migrate` (data migrations, [`22`](22-data-migrations.md)) | `asia-southeast1` |
| Document AI processors | `kredibel-ocr` (Enterprise Document OCR: witness for scanned pages, P0); `kredibel-form` and `kredibel-invoice` (escalation and thorough mode, P1) | `us` |
| Model Armor template (P1) | `kredibel-docs` | `asia-southeast1` (confirm in S4) |
| Memory Bank and Sessions (P1) | `kredibel-assistant`: created without deploying agent code; the assistant runs in `kredibel-web` ([ADR-014](adr/ADR-014-finance-assistant-tools-rag-memory.md)) | `asia-southeast1` if offered, else `us-central1` (Memory Bank may be multi-regional `us`) |
| Firestore vector indexes (P1) | `retrievalChunks`, `knowledgeChunks`, `labels` (768 dimensions, flat) from `contracts/firestore.indexes.json` | `asia-southeast1` |
| BigQuery datasets (P1) | `kredibel_agent_analytics` (agent events from the ADK plugin, [ADR-017](adr/ADR-017-agent-observability-on-google-cloud.md)); `kredibel_learning` (label exports, [ADR-016](adr/ADR-016-human-verified-labels-and-learning-loop.md)) | `asia-southeast1` |
| Cloud Storage bucket (agent content, P1) | `<PROJECT_ID>-kredibel-agent-content` (only where `AI_CONTENT_CAPTURE=synthetic`; deleted after 30 days) | `asia-southeast1` |
| Firebase project | same project | — |
| Service accounts | `kredibel-web`, `kredibel-worker`, `kredibel-tasks-invoker`, `kredibel-migrate` | — |
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
gcloud firestore databases create --database=kredibel --location="$REGION" --type=firestore-native \
  --enable-pitr --delete-protection || true                                                # ADR-021
gcloud firestore backups schedules create --database=kredibel --recurrence=daily --retention=7d || true
gcloud storage buckets create "gs://${PROJECT_ID}-kredibel-backups" --location="$REGION" \
  --uniform-bucket-level-access --public-access-prevention || true
gcloud storage buckets update "gs://${PROJECT_ID}-kredibel-backups" --lifecycle-file=infra/backups-lifecycle.json
gcloud storage buckets update "gs://${PROJECT_ID}-kredibel-docs" --versioning
gcloud tasks queues create kredibel-documents --location="$REGION" \
  --max-concurrent-dispatches=4 --max-attempts=3 --min-backoff=30s --max-backoff=300s || true
gcloud tasks queues create kredibel-months --location="$REGION" \
  --max-concurrent-dispatches=2 --max-attempts=3 --min-backoff=10s --max-backoff=120s || true

# 3. Service accounts
for sa in kredibel-web kredibel-worker kredibel-tasks-invoker kredibel-migrate; do
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
# Web enqueues documents and months; the worker enqueues months after reading a document
for q in kredibel-documents kredibel-months; do
  for sa in kredibel-web kredibel-worker; do
    gcloud tasks queues add-iam-policy-binding "$q" --location="$REGION" \
      --member="serviceAccount:$(SA $sa)" --role=roles/cloudtasks.enqueuer
  done
done
for sa in kredibel-web kredibel-worker; do
  gcloud iam service-accounts add-iam-policy-binding "$(SA kredibel-tasks-invoker)" \
    --member="serviceAccount:$(SA $sa)" --role=roles/iam.serviceAccountUser
done
# Migrations (docs/22): read/write documents, run exports, write only to the backups bucket
for role in roles/datastore.user roles/datastore.importExportAdmin roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$(SA kredibel-migrate)" --role="$role" --condition=None
done
gcloud storage buckets add-iam-policy-binding "gs://${PROJECT_ID}-kredibel-backups" \
  --member="serviceAccount:$(SA kredibel-migrate)" --role=roles/storage.objectAdmin
# Firestore's own service agent writes the export files
gcloud storage buckets add-iam-policy-binding "gs://${PROJECT_ID}-kredibel-backups" \
  --member="serviceAccount:service-$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')@gcp-sa-firestore.iam.gserviceaccount.com" \
  --role=roles/storage.admin
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
# Spec 003 adds --scenario S1 to upload a synthetic scenario's files into it.
(cd backend && uv run python -m scripts.seed_demo_workspace --org org_demo \
  --name "Sunrise Coffee Roasters" --entity COMPANY --trial-ends 2026-12-31 \
  --owner owner@demo.kredibel)
# P1 roles: add --accountant accountant@demo.kredibel --reviewer reviewer@demo.kredibel --viewer viewer@demo.kredibel

# 10. Assistant (P1): Memory Bank and a Sessions container, no agent code; prints MEMORY_BANK_ID and AGENT_SESSIONS_ID
uv run --project backend python backend/scripts/create_assistant_memory.py --project "$PROJECT_ID" \
  --location "$ASSISTANT_LOCATION" --display-name kredibel-assistant --memory-topics infra/memory-topics.yaml

# 11. Agent analytics and labels (P1): BigQuery datasets, content bucket, IAM
bq --location=asia-southeast1 mk --dataset "$PROJECT_ID:kredibel_agent_analytics"
bq --location=asia-southeast1 mk --dataset "$PROJECT_ID:kredibel_learning"
gcloud storage buckets create "gs://${PROJECT_ID}-kredibel-agent-content" --location=asia-southeast1 \
  --uniform-bucket-level-access --public-access-prevention
gcloud storage buckets update "gs://${PROJECT_ID}-kredibel-agent-content" --lifecycle-file=infra/agent-content-lifecycle.json
gcloud projects add-iam-policy-binding "$PROJECT_ID" --role=roles/bigquery.jobUser \
  --member="serviceAccount:kredibel-worker@$PROJECT_ID.iam.gserviceaccount.com"
gcloud projects add-iam-policy-binding "$PROJECT_ID" --role=roles/bigquery.jobUser \
  --member="serviceAccount:kredibel-web@$PROJECT_ID.iam.gserviceaccount.com"
# dataset-level: worker and web write agent events (plugin), web reads them for the Runs page
bq add-iam-policy-binding --member="serviceAccount:kredibel-worker@$PROJECT_ID.iam.gserviceaccount.com" \
  --role=roles/bigquery.dataEditor "$PROJECT_ID:kredibel_agent_analytics"
bq add-iam-policy-binding --member="serviceAccount:kredibel-web@$PROJECT_ID.iam.gserviceaccount.com" \
  --role=roles/bigquery.dataEditor "$PROJECT_ID:kredibel_agent_analytics"

# Knowledge chunks for search_knowledge (re-run when policy or help pages change; CI does it on deploy)
uv run --project backend python tools/knowledge/build.py --project "$PROJECT_ID"
```

`create_assistant_memory.py` uses the Agent Platform SDK to create a Memory Bank
(`client.memory_banks.create()`) with its configuration (custom topics limited to user preferences,
a time to live; confirmed in spike S5) and a Sessions container (an Agent Runtime instance with no
agent), and prints both IDs. Nothing is deployed to them; the assistant runs in `kredibel-web`.

`create_processors.py` uses the Document AI client with endpoint `us-documentai.googleapis.com`,
creates processors of type `OCR_PROCESSOR` (Enterprise Document OCR) and, with `--form --invoice`,
`FORM_PARSER_PROCESSOR` and `INVOICE_PROCESSOR` (confirm with `fetch_processor_types`), and prints the
processor IDs and the stable version names to use.

`firebase.json` (repository root) points the `kredibel` database's rules and indexes at `contracts/`.

---

## 4. Cloud Run services

| Setting | `kredibel-web` | `kredibel-worker` |
|---|---|---|
| Image | `asia-southeast1-docker.pkg.dev/<PROJECT_ID>/kredibel/app:<sha>` | same |
| `APP_ROLE` | `web` | `worker` |
| Auth | `--allow-unauthenticated` (the app verifies Firebase tokens) | `--no-allow-unauthenticated` (IAM) |
| Service account | `kredibel-web` | `kredibel-worker` |
| CPU / memory | 1 vCPU / 1 GiB | 2 vCPU / 2 GiB |
| Concurrency | 40 | 4 |
| Timeout | 60 s | 900 s |
| Min / max instances | 0 / 5 (set min 1 while recording the demo) | 0 / 3 |
| Labels | `app=kredibel,component=web` | `app=kredibel,component=worker` |

```bash
IMAGE=asia-southeast1-docker.pkg.dev/$PROJECT_ID/kredibel/app:$SHA
gcloud run deploy kredibel-worker --image="$IMAGE" --region="$REGION" --no-allow-unauthenticated \
  --service-account="$(SA kredibel-worker)" --cpu=2 --memory=2Gi --concurrency=4 --timeout=900 \
  --max-instances=3 --labels=app=kredibel,component=worker --env-vars-file=infra/env.worker.yaml
WORKER_URL=$(gcloud run services describe kredibel-worker --region="$REGION" --format='value(status.url)')
gcloud run deploy kredibel-web --image="$IMAGE" --region="$REGION" --allow-unauthenticated \
  --service-account="$(SA kredibel-web)" --cpu=1 --memory=1Gi --concurrency=40 --timeout=60 \
  --max-instances=5 --labels=app=kredibel,component=web --env-vars-file=infra/env.web.yaml \
  --update-env-vars=WORKER_URL="$WORKER_URL"
```

> If the organizers require a specific Cloud Run label for verification, add it to **both** deploy
> commands. `--labels` replaces the whole label set on every deploy.

### 4.1 Cloud Run job `kredibel-migrate`

Same image, `APP_ROLE=migrate`, runs pending data migrations ([`22`](22-data-migrations.md)).

```bash
gcloud run jobs deploy kredibel-migrate --image="$IMAGE" --region="$REGION" \
  --service-account="$(SA kredibel-migrate)" --tasks=1 --max-retries=1 --task-timeout=3600 \
  --cpu=1 --memory=1Gi --labels=app=kredibel,component=migrate \
  --set-env-vars=APP_ROLE=migrate,BACKUPS_BUCKET=${PROJECT_ID}-kredibel-backups \
  --command=python --args=-m,migrations,run
gcloud run jobs execute kredibel-migrate --region="$REGION" --wait --args=-m,migrations,run,--dry-run
```

---

## 5. Container image (`Dockerfile`, outline)

1. **Stage `web`** (`node:22-slim`): `npm ci`, generate API types from `contracts/openapi.yaml`, build
   with the public `VITE_FIREBASE_*` build args → `/fe/dist`.
2. **Stage `app`** (`python:3.12-slim`): install `uv`; `uv sync --frozen --no-dev`; copy
   `backend/app`, `contracts/`, and `/fe/dist` → `/app/static`; run as a non-root user; start
   `uvicorn app.main:app --host 0.0.0.0 --port 8080`.
3. System packages: none required (pikepdf, pdfplumber, pypdfium2, Pillow and openpyxl ship wheels).

`kredibel-web` serves `/app/static` with SPA fallback for non-`/api` paths and long-cache headers
for hashed assets. Firebase Hosting (`kredibel-app.web.app`) serves the same files and rewrites `/api/**`,
`/docs` and `/openapi.json` to `kredibel-web` ([ADR-018](adr/ADR-018-firebase-hosting-in-front-of-cloud-run.md)).

---

## 6. Configuration (environment variables)

### 6.1 Backend

| Variable | Example | Used by |
|---|---|---|
| `APP_ROLE` | `web` \| `worker` \| `all` | router mounting |
| `ENV_FILE` | `/secrets/.env` on Cloud Run \| `.env` (default) | the dotenv file `Settings` reads ([ADR-024](adr/ADR-024-runtime-configuration-in-secret-manager.md)) |
| `APP_VERSION` | git SHA | `/api/health`, logs |
| `K_SERVICE` | set by Cloud Run (`kredibel-web`, `kredibel-worker`) | `service` in every log line; `kredibel-<role>` when unset |
| `GOOGLE_CLOUD_PROJECT` | `<PROJECT_ID>` | all clients |
| `GOOGLE_CLOUD_LOCATION` | `global` | Gemini (ADK, google-genai) |
| `GOOGLE_GENAI_USE_VERTEXAI` | `TRUE` | ADK, google-genai |
| `REGION` | `asia-southeast1` | Tasks, Run URLs |
| `DOCS_BUCKET` | `<PROJECT_ID>-kredibel-docs` | storage |
| `TASK_QUEUE_MODE` | `cloud` \| `inline` | queue adapter |
| `TASKS_QUEUE_DOCUMENTS` / `TASKS_QUEUE_MONTHS` / `TASKS_LOCATION` | `kredibel-documents` / `kredibel-months` / `asia-southeast1` | web, worker |
| `MONTH_RUN_DELAY_SECONDS` | `20` (debounce: changes within the delay become one month run) | web, worker |
| `WORKER_URL` | `https://kredibel-worker-…run.app` | web, worker (task target) |
| `TASKS_INVOKER_SA` | `kredibel-tasks-invoker@…` | web, worker (OIDC token on tasks) |
| `DOCAI_LOCATION` | `us` | worker |
| `DOCAI_OCR_PROCESSOR_ID` / `DOCAI_OCR_VERSION` | `abc123…` / Enterprise OCR v2 version name | worker |
| `DOCAI_FORM_PROCESSOR_ID` / `DOCAI_FORM_VERSION` | `ghi789…` / Form Parser v2.0 version name (P1) | worker |
| `DOCAI_INVOICE_PROCESSOR_ID` / `DOCAI_INVOICE_VERSION` | `def456…` / Invoice Parser v2.0 version name (P1) | worker |
| `EXTRACTION_MODE` | `adaptive` (default) \| `thorough` (evals) | worker |
| `EXTRACTION_ESCALATION` | `off` (P0) \| `on` (P1) | worker |
| `ESCALATION_MAX_PAGES_PER_MONTH` | `30` (capped by the plan's `escalationPagesPerMonth`) | worker |
| `READ_MEDIA_RESOLUTION` | `high` (or `ultra_high` if spike S1 shows it pays off) | worker |
| `PAGE_CONCURRENCY` | `6` | worker |
| `EXTRACTION_CACHE` | `on` (default) \| `ocr_only` (evals: re-read with Gemini, reuse OCR) \| `off` | worker |
| `PREFILL_ON_UPLOAD` | `off` (P1) | web |
| `RUNS_ENABLED` | `true` \| `false` (kill switch: new reading and runs return `503 RUNS_DISABLED`) | web |
| `RUN_QUOTA_PER_ORG_PER_DAY` | `80` (global ceiling above each plan's `monthRunsPerDay`) | web, worker |
| `SIGNUP_MODE` | `open` \| `invite_only` \| `closed` | web |
| `MAX_WORKSPACES` | `15` | web |
| `PLANS_FILE` | `/app/contracts/plans.v1.yaml` | both |
| `MODEL_FAST` / `MODEL_LITE` / `MODEL_EMBEDDING` | see [`06`](06-agent-design.md) §11 | worker, web |
| `MODEL_ARMOR_LOCATION` / `MODEL_ARMOR_TEMPLATE` | `asia-southeast1` / `kredibel-docs` | worker (P1) |
| `MEMORY_BANK_ID` / `AGENT_SESSIONS_ID` / `ASSISTANT_LOCATION` | IDs from bootstrap step 10 / `asia-southeast1` | web (assistant memories and sessions, P1) |
| `ASSISTANT_MEMORY` | `on` \| `off` (sessions only) | web (P1) |
| `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS` | Set from `AI_CONTENT_CAPTURE` at start-up (`false` unless `synthetic`); must be explicit outside Agent Runtime | both |
| `AI_CONTENT_CAPTURE` | `off` (default) \| `synthetic` (prompts and responses in traces and agent events; refused unless `DATA_CLASS=synthetic`), [ADR-017](adr/ADR-017-agent-observability-on-google-cloud.md) | both |
| `DATA_CLASS` | `real` on the services and in local development, where the owner's own documents run ([ADR-022](adr/ADR-022-real-documents-in-production.md)); `synthetic` (the default) for tests and evals | both |
| `FIRESTORE_DATABASE` | `kredibel` ([ADR-021](adr/ADR-021-kredibel-firestore-database.md)); `(default)` for the emulator and tests | both, migrate job, scripts |
| `ANALYTICS_DATASET` / `AGENT_CONTENT_BUCKET` | `kredibel_agent_analytics` / `<PROJECT_ID>-kredibel-agent-content` | both (P1) |
| `LEARNING_FILE` / `CATEGORIES_FILE` | `/app/contracts/policy/learning.v1.yaml` / `categories.v1.yaml` | both |
| `POLICY_DIR` | `/app/contracts/policy` | both |
| `EXPLAINER_MAX_ATTEMPTS` / `DOCUMENT_RUN_BUDGET_SECONDS` / `MONTH_RUN_BUDGET_SECONDS` | `2` / `600` / `120` | worker |
| `FEATURE_MODEL_ARMOR`, `FEATURE_VISUAL_FORENSICS`, `FEATURE_REVISION_DIFF`, `FEATURE_ASSISTANT`, `FEATURE_ROLES`, `FEATURE_RUN_GRAPH`, `FEATURE_SIGN_OFF`, `FEATURE_LABELS`, `FEATURE_AGENT_ANALYTICS`, `FEATURE_DATASET_EXPORT` | `false` | both |
| `TRACE_EXPORT` | `cloud` on Cloud Run \| `otlp` for local Jaeger \| `none` (default) | both: where workflow spans go ([`17`](17-observability.md) §2) |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | `http://127.0.0.1:4318/v1/traces` | local traces-only OTLP/HTTP endpoint when `TRACE_EXPORT=otlp` |
| `LOG_LEVEL` | `INFO` | both |
| `BACKUPS_BUCKET` | `<PROJECT_ID>-kredibel-backups` | migrate job |
| `MIGRATION_MAX_OPS_PER_SEC` / `MIGRATION_PAGE_SIZE` | `500` / `300` | migrate job |
| `MIGRATION_EXPORT_BEFORE_RUN` | `true` (shared environments) \| `false` (emulator) | migrate job |
| `EVAL_JUDGE_MODEL` | a Gemini model on Agent Platform (DeepEval judge, [`15`](15-testing-and-evaluation.md) §5.1) | evals only |

Production values live in one Secret Manager secret, **`kredibel-env`**
([ADR-024](adr/ADR-024-runtime-configuration-in-secret-manager.md)): a dotenv file that both services
mount at `/secrets/.env` and read through `ENV_FILE`. `infra/env.web.yaml` and `infra/env.worker.yaml`
hold only what differs per service (`APP_ROLE`, `ENV_FILE`; both deploys add `WORKER_URL`, the
worker's own URL: web queues document runs, the worker queues month runs to itself). No
server API key is part of it: all Google access uses the service accounts.

```bash
make env-pull      # latest kredibel-env → .env.production (gitignored, mode 600)
make env-keys      # which keys are set, never their values
make env-push      # add a version from .env.production; then make deploy
```

`infra/kredibel-env.example` is the committed template; keep it in step with `Settings`.

### 6.2 Frontend (build-time, public)

`VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_AUTH_DOMAIN`, `VITE_FIREBASE_PROJECT_ID`,
`VITE_FIREBASE_APP_ID`, `VITE_FIRESTORE_DATABASE` (from `kredibel-env`; the build stops when the API
key is empty), `VITE_APP_VERSION` (the commit). **`VITE_` values are inlined into the public bundle.**
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

Kredibel deploys to its own database, `kredibel` ([ADR-021](adr/ADR-021-kredibel-firestore-database.md)):
`firebase.json` lists only that database, so rules and indexes never reach another app's. The CLI
still prints "released rules … to cloud.firestore"; the release that actually changes is
`cloud.firestore/kredibel`, which the `curl` above shows.

---

## 8. CI/CD (`cloudbuild.yaml`)

| Step | Image | Does |
|---|---|---|
| 1 `backend-check` | `python:3.12-slim` + uv | ruff, pyright, import-linter, repo checks (schema drift, policy load), pytest incl. migrations on the emulator |
| 2 `frontend-check` | Playwright image (`node:22` + Chromium) | `npm ci`, eslint, tsc, vitest, `make tokens-check`, `no_raw_styles.py`, Storybook tests with axe, Playwright visual and axe at 390/834/1440 ([`15`](15-testing-and-evaluation.md) §2.6) |
| 3 `secret-scan` | `python:3.12-slim` | `tools/checks/scan_secrets.py` over the repo |
| 4 `build` | `gcr.io/cloud-builders/docker` | build with the `VITE_` values from `kredibel-env` (stops if the API key is empty), tag `:$SHORT_SHA` and `:latest` |
| 5 `push` | docker | push to Artifact Registry |
| 5a `indexes` | `node:22-slim` + firebase CLI | `firebase deploy --only firestore:indexes,firestore:rules`; wait until every index is `READY` |
| 5a′ `knowledge` (P1) | `python:3.12-slim` + uv | `tools/knowledge/build.py`: embed changed policy and help passages into `knowledgeChunks` |
| 5b `migrate` | cloud-sdk | update the `kredibel-migrate` job to the new image; dry run; run, where the job itself exports to the backups bucket first when migrations are pending (`MIGRATION_EXPORT_BEFORE_RUN=true`, its own service account); stop the build on `FAILED` or `failed > 0` ([`22`](22-data-migrations.md) §7) |
| 6 `deploy-worker` | `gcr.io/google.com/cloudsdktool/cloud-sdk` | `gcloud run deploy kredibel-worker …` with `kredibel-env` mounted at `/secrets/.env` |
| 7 `deploy-web` | cloud-sdk | read `WORKER_URL`; `gcloud run deploy kredibel-web …` |
| 7a `hosting` | docker + `node:22-slim` | copy `/app/static` out of the new image; `firebase deploy --only hosting` (ADR-018) |
| 8 `smoke` | cloud-sdk | `$WEB_URL/api/health` and `https://kredibel-app.web.app/api/health` both return the new `APP_VERSION` |
| 9 `lighthouse` | Playwright image | Lighthouse CI (mobile) on the deployed dashboard and review queue with the demo user; report only during the competition |

Triggered manually (`make deploy` → `gcloud builds submit`) during the competition, so a half-finished
push never redeploys the demo by accident.

---

## 9. Runbook

| Situation | Action |
|---|---|
| Roll back | `gcloud run services update-traffic kredibel-web --to-revisions=<prev>=100 --region=$REGION` (same for worker) |
| Document stuck in `READING` | Check `kredibel-documents` and worker logs for `runId`; `scripts/requeue.py --doc …` re-enqueues (idempotent) |
| Month stuck in `RECONCILING` | Check `kredibel-months`; `scripts/requeue.py --month 2026-03 --org …` bumps the generation and enqueues a fresh run |
| Assistant answers without memories | `MEMORY_BANK_ID` wrong or in another location; `ASSISTANT_MEMORY=off` keeps the assistant working with sessions only |
| `403` from worker in logs | `run.invoker` binding for `kredibel-tasks-invoker` missing (bootstrap step 6) |
| Task creation fails with permission error | `kredibel-web` lacks `iam.serviceAccountUser` on the invoker SA |
| Gemini `404 model not found` | Model ID not available in the project/location; change `MODEL_*`, redeploy |
| Document AI `INVALID_ARGUMENT` on pages | An OCR request with more than 15 pages; check the batching in `docai_ocr` |
| New user stuck on "Finishing setup…" | Custom claims not set: `kredibel-web` lacks `roles/firebaseauth.admin`, or the client didn't refresh its token |
| Sign-ups must stop now | `SIGNUP_MODE=closed` on `kredibel-web` (existing workspaces keep working) |
| Google sign-in popup blocked | Cloud Run URL missing from Firebase authorized domains; CSP `frame-src` |
| Migration `FAILED` | `make migrate-status ENV=…`; read the job logs for `migration_id`; fix forward with a new migration; rerun resumes from the checkpoint |
| Bad data after a migration | [`22`](22-data-migrations.md) §8: export the collection group at a time before it (PITR), compare in a scratch database, write corrections with a new migration |
| Migration lock stuck | The lease expires after 10 minutes; `make migrate-unlock ENV=…` only if the job is confirmed dead |
| Cold start during demo | `gcloud run services update kredibel-web --min-instances=1` (and worker) before recording; set back afterwards |

---

## 10. Cost guardrails

The full analysis, including the database comparison, is in [`21-cost-analysis.md`](21-cost-analysis.md).

- Budget equal to the team's limit, with alerts at 50% / 90% / 100%.
- Firestore database `kredibel` (ADR-021); the free tier covers one database per project and goes to
  `(default)`, so Kredibel pays from the first read (cents at demo volumes); no Cloud SQL.
- Cloud Run scales to zero; Firestore and GCS are pay-per-use.
- Adaptive reading (`EXTRACTION_MODE=adaptive`): one AI reading per page, free text-layer witness, OCR
  only for scans; per-page extraction cache; exact duplicates never read; ledger files parsed by code.
- Plan limits per workspace (`contracts/plans.v1.yaml`), `SIGNUP_MODE`, `MAX_WORKSPACES`,
  `RUN_QUOTA_PER_ORG_PER_DAY` and the `RUNS_ENABLED` kill switch protect the public demo.
- Artifact Registry cleanup policy keeps the 3 most recent images:
  `gcloud artifacts repositories set-cleanup-policies kredibel --location="$REGION" --policy=infra/ar-cleanup.json`
- Per-run usage is recorded (`runs.usage`) and summarized by `make evals` (E-PERF).
