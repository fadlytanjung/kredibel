#!/usr/bin/env bash
# The kredibel-env secret: production configuration as one dotenv payload (ADR-024).
#   infra/env-secret.sh keys  [file]   which keys are set, never their values
#   infra/env-secret.sh push  [file]   add a version from the file (default .env.production)
#   infra/env-secret.sh pull  [file]   write the latest version to the file (mode 600)
#   infra/env-secret.sh check [file]   compare the file with the latest version by SHA-256
# Never print the payload: tool output and terminals end up in transcripts.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
SECRET="${SECRET_NAME:-kredibel-env}"
cmd="${1:-}"
file="${2:-.env.production}"

keys() {
  awk -F= '/^[A-Za-z_][A-Za-z0-9_]*=/ {
    k=$1; v=substr($0, index($0,"=")+1); gsub(/^"|"$/,"",v)
    printf "%-34s %s (len=%d)\n", k, (length(v)>0 ? "SET" : "EMPTY"), length(v)
  }' "$1"
}
remote_sha() {
  gcloud secrets versions access latest --secret="$SECRET" --project="$PROJECT_ID" 2>/dev/null \
    | shasum -a 256 | cut -d' ' -f1
}
local_sha() { shasum -a 256 "$1" | cut -d' ' -f1; }

case "$cmd" in
  keys)
    keys "$file"
    ;;
  push)
    [ -f "$file" ] || { echo "No $file: copy infra/kredibel-env.example and fill it in." >&2; exit 1; }
    for k in VITE_FIREBASE_API_KEY VITE_FIREBASE_APP_ID FIRESTORE_DATABASE DATA_CLASS TASK_QUEUE_MODE; do
      grep -qE "^$k=.+" "$file" || { echo "$k is empty in $file" >&2; exit 1; }
    done
    if grep -qE '^(APP_ROLE|WORKER_URL|ENV_FILE|GEMINI_API_KEY|GOOGLE_API_KEY|FIRESTORE_EMULATOR_HOST)=' "$file"; then
      echo "$file sets a per-service or local-only key; see infra/kredibel-env.example" >&2
      exit 1
    fi
    if ! gcloud secrets describe "$SECRET" --project="$PROJECT_ID" >/dev/null 2>&1; then
      gcloud secrets create "$SECRET" --project="$PROJECT_ID" \
        --replication-policy=automatic --labels=app=kredibel,managed-by=cli
    fi
    if [ "$(remote_sha || true)" = "$(local_sha "$file")" ]; then
      echo "$SECRET already matches $file"
      exit 0
    fi
    gcloud secrets versions add "$SECRET" --project="$PROJECT_ID" --data-file="$file"
    [ "$(remote_sha)" = "$(local_sha "$file")" ] || { echo "upload does not match $file" >&2; exit 1; }
    echo "Pushed. Services pick it up on their next revision: make deploy"
    ;;
  pull)
    umask 077
    gcloud secrets versions access latest --secret="$SECRET" --project="$PROJECT_ID" > "$file"
    echo "Wrote $file"
    keys "$file"
    ;;
  check)
    if [ "$(remote_sha)" = "$(local_sha "$file")" ]; then
      echo "$file matches the latest $SECRET"
    else
      echo "$file differs from the latest $SECRET" >&2
      exit 1
    fi
    ;;
  *)
    sed -n '2,7p' "$0"
    exit 2
    ;;
esac
