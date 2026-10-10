---
trigger: always_on
description: Security and data-handling rules. Applies to every change, including scripts and infra.
---

# Security and data

- **Synthetic data only.** Never add real customer documents, names, account numbers or tax IDs. Test
  and demo files come from `tools/synthetic/`.
- **No secrets** in code, config, images, logs, commit messages or tool output. Use ADC and service
  accounts. If a secret is ever needed, it goes to Secret Manager and is mounted as an env var.
- **Never print** tokens, keys or credentials to stdout, even while debugging.
- `VITE_*` variables are public; never put a server-side value behind one.
- Every repository call takes `org_id` (the workspace) from the verified token's claim. A foreign ID
  returns 404. Custom claims are set only by server code (workspace creation, invite acceptance) and
  the bootstrap script.
- Personal data minimization: accept full account numbers only on input, store them masked plus a hash
  in `orgPrivate/`, never return or log them; accept only the last 4 digits of ID numbers.
- Plan `limitOverrides` and `system/` documents are server-only; no API writes them.
- Firestore rules deny all client writes. Do not relax `contracts/firestore.rules` without a test and
  an ADR.
- Uploaded documents are untrusted: sniff type by magic bytes, enforce limits, never execute embedded
  content, never pass a quarantined document to a model.
- Model output is untrusted: validate with Pydantic; render markdown safely; resolve citations only
  against known IDs.
- A change to an auth, isolation or decision guard needs a test in the same commit.
