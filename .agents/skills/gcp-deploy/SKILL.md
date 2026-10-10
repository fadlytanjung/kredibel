---
name: gcp-deploy
description: Deploys Kredibel to Google Cloud (Cloud Build → Artifact Registry → Cloud Run web and worker), verifies the deployment, and rolls back if needed. Use when asked to deploy, release, redeploy, check the deployed app, or fix a deployment problem.
---

# Deploy and verify

## Before

- `make check` is green on the commit being deployed.
- `docs/16-infrastructure-and-deployment.md` §3 bootstrap has been run for this project (APIs, SAs,
  IAM, queue, bucket, Firestore, processors, Firebase).
- `infra/env.web.yaml` / `infra/env.worker.yaml` contain current values (processor IDs, model IDs,
  feature flags). No secrets in them.

## Deploy

```bash
make deploy        # gcloud builds submit --config cloudbuild.yaml
```

Cloud Build runs checks, builds one image, deploys `kredibel-worker` (IAM-only) then `kredibel-web`
(with `WORKER_URL`), then smoke-tests `/api/health`.

## Verify

1. `curl -fsS https://<web-url>/api/health` shows the new `version`.
2. `curl -s -o /dev/null -w "%{http_code}" https://<worker-url>/tasks/analyze-case -X POST` → `403`.
3. Sign in on the web URL in a private window; open a seeded case.
4. Start a run on S1; confirm live progress and `READY_FOR_REVIEW`.
5. Firestore rules: verify the released ruleset (docs/16 §7) if rules changed.
6. Cloud Logging: no `ERROR` entries for the run; trace present.

## Roll back

```bash
gcloud run revisions list --service kredibel-web --region asia-southeast1
gcloud run services update-traffic kredibel-web --to-revisions=<previous>=100 --region asia-southeast1
# same for kredibel-worker
```

## Never

- Print or paste credentials or tokens into the terminal output.
- Deploy with `--labels` missing required labels (the flag replaces the whole set).
- Leave `min-instances=1` on after the demo recording (cost).
