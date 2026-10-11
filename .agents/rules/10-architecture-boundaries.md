---
trigger: always_on
description: Architecture boundaries and the model/code boundary. Applies to all backend and agent code.
---

# Architecture boundaries

## Layers (backend)

- `domain/` is pure: no Google SDKs, no FastAPI, no ADK, no network, no file I/O, no `datetime.now()`.
- `ports/` declares `typing.Protocol` interfaces; `adapters/` implements them with Google/OSS SDKs.
- `services/` and `agents/` depend on `domain` and `ports` only; adapters are injected through
  `create_app(settings, deps)`, `build_document_workflow(deps)` and `build_month_workflow(deps)`.
- `api/` routers are thin: parse, call a service, map errors. No business logic in routers.
- Every new external dependency gets a port and an in-memory fake in `backend/tests/fakes/`.

## Model / code boundary

- Models read pages, classify, propose ledger mappings, categorize the long tail, give visual
  opinions, write explanations and answer questions.
- Code computes every number, duplicate, match, figure, money flow, verdict, risk level and state
  change. `reconcile_month` is pure and order-independent; user decisions are its inputs.
- Every model call has a prompt file, a Pydantic output schema, a model setting from env, and goes
  through the `GeminiGateway` port or an ADK `Agent` node with `output_schema`.
- Model output never writes matches, risk levels, review resolutions, duplicate decisions, policy,
  plan limits or the workspace profile (profile data and ledger mappings only as proposals a person
  accepts).
- The AI page reader gets the page **image** only; the text layer and OCR are the witness. Never give
  the reader the witness's words (it would destroy the independence the corroboration rule needs).
- Plan limits are checked through `EntitlementService` (pure rules in `domain/plans.py`); never
  hard-code a limit or branch on a plan ID.

## Platform

- Managed services and AI from Google Cloud/Firebase only (Cloud Run, Cloud Tasks, Firestore incl.
  vector search, Cloud Storage, Document AI, Gemini on Agent Platform, Agent Platform Sessions and
  Memory Bank, Model Armor, Firebase Auth, Cloud Build, Cloud Trace). Open-source libraries in our
  containers are fine (e.g. DeepEval for evals, with a Gemini judge).
- Orchestration with ADK. Do not introduce LangChain/LangGraph or third-party AI APIs.
- Regions and model IDs are configuration, never literals.
