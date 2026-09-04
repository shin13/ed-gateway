# ED Gateway State

Updated: 2026-09-04 (Asia/Shanghai)

## Status

The research MVP vertical slice is complete on branch `codex/build-ed-gateway-mvp`. The local Docker Compose stack is intentionally left running for review:

- Chainlit: `http://127.0.0.1:8000`
- FastAPI/OpenAPI: `http://127.0.0.1:8001/docs`
- PostgreSQL: internal Compose network only

## Implemented

- Thin Chainlit adapter with the required Traditional Chinese starter, early-finish action, new synthetic-session action, Markdown draft, and structured JSON side view.
- FastAPI orchestration for session creation, one-question turns, retrieval, early finish, warning escalation, draft retrieval, liveness, and readiness.
- Shared Pydantic interview state and one question engine for chest discomfort, dizziness, fever, lower-back pain, and other complaints.
- Clause-aware safety interpretation, explicit answer statuses, provenance, contradiction clarification, conservative ambiguity escalation, and provider-neutral LLM integration.
- Deterministic nurse-review drafts with all required sections, UTC update time, missing and contradictory fields, no formal triage score, and the mandatory disclaimer.
- PostgreSQL JSONB state, ordered raw messages, append-only events, draft revisions, Alembic migration, and retained named volume.
- Environment allowlists, secret types, localhost host bindings, non-root application containers, and documented privacy/production gaps.

## Verified locally

- `uv sync --dev`: passed.
- `uv run pytest`: 58 passed; the separately invoked Compose smoke is skipped when its URL is absent.
- `uv run ruff check .`: passed after final formatting.
- `uv run mypy`: passed for 26 source files.
- `docker compose config --quiet`: passed.
- `docker compose up --build -d`: db, api, and web became healthy.
- `uv run pytest -m smoke` with the running API: 1 passed, covering normal, escalation, PostgreSQL, session, and draft paths.
- Browser observation: research notice, exact first question, both actions, full Markdown draft, and JSON side view rendered.
- Restart proof: api/web restart retained session `29d9dc20-5c53-42db-8601-efd8d8b8e020` and draft revision 1 in the named volume.
- PostgreSQL inspection: session state is `jsonb`; sessions, ordered messages, events, and drafts are populated.

## Boundaries and next work

- This is local mock-functional research evidence, not clinical validation, live-provider validation, deployment, medical-device, privacy, or production-readiness evidence.
- Resolve and approve every item in `docs/open-clinical-decisions.md` before clinical use.
- Add hospital SSO/RBAC, encryption and key management, retention/deletion policy, privacy review, security testing, and human-confirmed EHR integration before production consideration.
- Evaluate the live OpenAI-compatible adapter with approved synthetic data and add concurrency/idempotency controls before multi-user trials.
