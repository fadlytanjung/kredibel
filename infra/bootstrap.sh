#!/usr/bin/env bash
# Kredibel — Infrastructure Bootstrap Script
# Provisions all Google Cloud and Firebase resources idempotently.
# See docs/16-infrastructure-and-deployment.md §3

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-cloud-hack2skill}"
REGION="${REGION:-asia-southeast1}"

echo "==> Configuring gcloud project: $PROJECT_ID, region: $REGION"
gcloud config set project "$PROJECT_ID"

echo "==> 1. Enabling required Google Cloud APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  cloudtasks.googleapis.com \
  documentai.googleapis.com \
  aiplatform.googleapis.com \
  modelarmor.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  cloudtrace.googleapis.com \
  firebase.googleapis.com \
  firebasehosting.googleapis.com \
  identitytoolkit.googleapis.com

echo "==> 2. Creating Artifact Registry, Cloud Storage buckets, Firestore database, and Task Queues..."
gcloud artifacts repositories create kredibel \
  --repository-format=docker \
  --location="$REGION" || true
if [ -f infra/ar-cleanup.json ]; then
  gcloud artifacts repositories set-cleanup-policies kredibel \
    --location="$REGION" \
    --policy=infra/ar-cleanup.json \
    --no-dry-run || true
fi

gcloud storage buckets create "gs://${PROJECT_ID}-kredibel-docs" \
  --location="$REGION" \
  --uniform-bucket-level-access \
  --public-access-prevention || true
gcloud storage buckets update "gs://${PROJECT_ID}-kredibel-docs" --versioning || true

# Kredibel's own database in the shared project (ADR-021).
gcloud firestore databases create --database=kredibel \
  --location="$REGION" \
  --type=firestore-native --enable-pitr --delete-protection || true
gcloud firestore backups schedules create --database=kredibel --recurrence=daily --retention=7d || true

gcloud storage buckets create "gs://${PROJECT_ID}-kredibel-backups" \
  --location="$REGION" \
  --uniform-bucket-level-access \
  --public-access-prevention || true
if [ -f infra/backups-lifecycle.json ]; then
  gcloud storage buckets update "gs://${PROJECT_ID}-kredibel-backups" --lifecycle-file=infra/backups-lifecycle.json || true
fi

gcloud tasks queues create kredibel-documents --location="$REGION" \
  --max-concurrent-dispatches=4 --max-attempts=3 --min-backoff=30s --max-backoff=300s || true

gcloud tasks queues create kredibel-months --location="$REGION" \
  --max-concurrent-dispatches=2 --max-attempts=3 --min-backoff=10s --max-backoff=120s || true

echo "==> 3. Creating Service Accounts..."
for sa in kredibel-web kredibel-worker kredibel-tasks-invoker kredibel-migrate; do
  gcloud iam service-accounts create "$sa" --display-name="$sa" || true
done

SA() { echo "$1@${PROJECT_ID}.iam.gserviceaccount.com"; }

echo "==> 4. Binding IAM roles..."
for role in roles/datastore.user roles/logging.logWriter roles/cloudtrace.agent \
            roles/monitoring.metricWriter roles/aiplatform.user; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$(SA kredibel-web)" --role="$role" --condition=None || true
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$(SA kredibel-worker)" --role="$role" --condition=None || true
done

for role in roles/documentai.apiUser roles/modelarmor.user; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$(SA kredibel-worker)" --role="$role" --condition=None || true
done

for sa in kredibel-web kredibel-worker; do
  gcloud storage buckets add-iam-policy-binding "gs://${PROJECT_ID}-kredibel-docs" \
    --member="serviceAccount:$(SA $sa)" --role=roles/storage.objectAdmin || true
done

# Web sets Firebase custom claims when a workspace is created or an invite accepted
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$(SA kredibel-web)" \
  --role=roles/firebaseauth.admin --condition=None || true

# Cloud Build deploys services and the migrate job, Firestore rules and indexes, the pre-release
# export (docs/22 §7) and Hosting (ADR-018). Builds run as the project's default build SA, which
# is the Compute default SA on new projects, so look it up instead of assuming the legacy one.
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
BUILD_SA="$(gcloud builds get-default-service-account --project="$PROJECT_ID" --format='value(serviceAccountEmail)' | sed 's#.*/##')"
for role in roles/run.admin roles/iam.serviceAccountUser roles/artifactregistry.writer \
  roles/datastore.indexAdmin roles/firebaserules.admin roles/datastore.importExportAdmin \
  roles/firebasehosting.admin roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${BUILD_SA}" --role="$role" --condition=None || true
done

# Cloud Tasks enqueuing
for q in kredibel-documents kredibel-months; do
  for sa in kredibel-web kredibel-worker; do
    gcloud tasks queues add-iam-policy-binding "$q" --location="$REGION" \
      --member="serviceAccount:$(SA $sa)" --role=roles/cloudtasks.enqueuer || true
  done
done

for sa in kredibel-web kredibel-worker; do
  gcloud iam service-accounts add-iam-policy-binding "$(SA kredibel-tasks-invoker)" \
    --member="serviceAccount:$(SA $sa)" --role=roles/iam.serviceAccountUser || true
done

# Migrations: read/write documents, run exports, write only to backups bucket
for role in roles/datastore.user roles/datastore.importExportAdmin roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$(SA kredibel-migrate)" --role="$role" --condition=None || true
done

gcloud storage buckets add-iam-policy-binding "gs://${PROJECT_ID}-kredibel-backups" \
  --member="serviceAccount:$(SA kredibel-migrate)" --role=roles/storage.objectAdmin || true

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
gcloud storage buckets add-iam-policy-binding "gs://${PROJECT_ID}-kredibel-backups" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-firestore.iam.gserviceaccount.com" \
  --role=roles/storage.admin || true

echo "==> 5. Creating Cloud Run migrate job..."
gcloud run jobs create kredibel-migrate \
  --image="asia-southeast1-docker.pkg.dev/${PROJECT_ID}/kredibel/app:latest" \
  --region="$REGION" \
  --service-account="$(SA kredibel-migrate)" \
  --tasks=1 --max-retries=1 --task-timeout=3600s --cpu=1 --memory=1Gi \
  --labels=app=kredibel,component=migrate \
  --set-env-vars=APP_ROLE=migrate,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},FIRESTORE_DATABASE=kredibel,BACKUPS_BUCKET=${PROJECT_ID}-kredibel-backups \
  --command=python --args=-m,migrations,run || true

echo "==> 6. Ensuring Firebase Hosting site is created..."
npx --yes firebase-tools hosting:sites:create kredibel-app --project "$PROJECT_ID" --non-interactive || true

echo "==> 7. Seeding the demo workspace (free trial to 31 Dec 2026 with demo limits, spec 013)..."
# Needs ADC with Firebase Auth admin and Firestore write on $PROJECT_ID. The owner's password is
# set in the Firebase console, never here.
(cd "$(dirname "$0")/../backend" && GOOGLE_CLOUD_PROJECT="$PROJECT_ID" uv run python -m scripts.seed_demo_workspace \
  --org org_demo --name "Sunrise Coffee Roasters" --entity COMPANY --trial-ends 2026-12-31 \
  --owner owner@demo.kredibel --project "$PROJECT_ID")

echo "==> Bootstrap completed successfully for project $PROJECT_ID."

