# ED Gateway State

_Last updated: 2026-09-04 — Session: MVP build closeout_

## Status

The research MVP vertical slice is complete and committed on `codex/build-ed-gateway-mvp`. It is ready for the user's synthetic live validation and a later feedback-driven revision session. No code work is in progress.

The local Docker Compose stack is intentionally left running:

- Chainlit: `http://127.0.0.1:8000`
- FastAPI/OpenAPI: `http://127.0.0.1:8001/docs`
- PostgreSQL: internal Compose network only, named volume retained
- Current provider: `mock`; no live LLM provider has been validated

## What Was Done This Session

- Built the complete Chainlit → FastAPI → shared interview engine → PostgreSQL → nurse-draft flow.
- Added versioned schemas, questions, 12-category safety rules, context rules, deterministic drafts, migrations, Docker Compose, and engineering documentation.
- Added clause-aware safety interpretation, explicit missing/unknown/refused states, provenance, contradiction clarification, provider-neutral LLM extraction, and raw-message-first persistence.
- Verified normal completion, partial completion, warning escalation, four shared-engine complaint fixtures, browser rendering, PostgreSQL storage, and persistence across api/web restart.

## Decisions Made

- The Downloads research directory remains read-only; this repository is the only code source of truth.
- A live LLM may propose normalized extraction, but Pydantic validation, deterministic safety rules, and deterministic drafts remain authoritative.
- Safety-positive findings stop ordinary questioning; unresolved safety ambiguity gets one clarification and then conservative nurse escalation.
- The AI never assigns TTAS level, diagnoses, recommends treatment, estimates missing measurements, or submits a final hospital record.
- Manual validation must use synthetic data. Mock-functional, live-provider, clinical, and production evidence remain separate claims.

## Verified Evidence

- Commit `18dcd50` — `feat: build ED Gateway research MVP`.
- `uv run pytest`: 58 passed; 1 Compose smoke skipped when no running URL is configured.
- Running-stack smoke: 1 passed against the real Compose API and PostgreSQL.
- Ruff, mypy for 26 source files, and `git diff --check`: passed.
- Final `docker compose ps`: db, api, and web are healthy.
- Browser observation: research notice, exact first question, both actions, complete Markdown draft, and structured JSON side view rendered.
- Restart proof retained session `29d9dc20-5c53-42db-8601-efd8d8b8e020` and draft revision 1.

## In Progress / Incomplete

- User synthetic live validation and feedback have not yet occurred.
- The OpenAI-compatible provider path is implemented but has not been exercised with a live endpoint.
- Clinical validity, institutional workflow fit, privacy controls, security review, multi-user concurrency/idempotency, and production deployment are outside current evidence.

## Known Issues / Blockers

- No implementation blocker is active.
- Clinical governance questions remain in `docs/open-clinical-decisions.md`.
- Production requirements remain in `docs/privacy-and-production-gaps.md`.

## Next Steps

1. Follow `docs/live-validation-checklist.md` using synthetic scenarios only; first record whether validation uses the current mock provider or an approved live provider.
2. For each issue, capture the scenario, exact synthetic answer sequence, expected behavior, actual behavior, approximate UTC/local time, and a screenshot when useful. Never include credentials or real patient data.
3. In the next coding session, begin by reading `CLAUDE.md`, this file, and the validation feedback; reproduce each issue before revising code.

## Context for Next Session

Start from commit `18dcd50` on `codex/build-ed-gateway-mvp`. The stack was left running and the database volume was not reset. Re-check `git status`, `docker compose ps`, `/health/ready`, and the configured `LLM_PROVIDER` before treating old runtime state as current.
