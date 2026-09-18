# ED Gateway Repository Guidance

## Authority and scope

- `GOAL.md` defines the product and engineering boundary.
- The research-material directory under `/Users/shin/Downloads/` is read-only.
- This repository is the only code source of truth.
- Use Traditional Chinese for patient-facing text and English for code and engineering docs.

## Safety invariants

- Never diagnose, recommend treatment or medication, promise safe waiting, or assign a formal TTAS level.
- Keep the 12 warning categories in versioned configuration and label them as a clinical-review draft.
- Preserve verbatim text separately from normalized values and always retain provenance.
- A positive configured warning stops ordinary questions and requests immediate nurse review.
- Safety ambiguity gets one direct clarification, then conservative escalation.
- LLM warning-sign proposals are add-only: they may flag a category the deterministic keyword sweep
  missed, never clear or downgrade one it found. See `docs/multilingual-safety-detection-design.md`.
- Every draft must end with the required nurse-review disclaimer.
- Use synthetic data only; never log raw interview messages to stdout.

## Architecture

- Keep Chainlit as a thin API client; clinical logic belongs in `src/ed_gateway/application`.
- Keep Pydantic domain models independent from SQLAlchemy.
- Persist raw messages before extraction, then persist the state/event/response outcome.
- Treat live LLM output as a validated proposal; deterministic safety rules and drafts remain authoritative.
- Add questions and clinical rules through `config/`, not hardcoded complaint-specific flows.

## Development

- Python support is `>=3.12,<3.14`; dependencies are managed with `uv`.
- Run `uv run pytest`, `uv run ruff check .`, `uv run mypy`, and `git diff --check`.
- Use `docker compose up --build -d` for the supported full stack.
- Keep `.env`, credentials, real patient data, and generated local state out of Git.
- `POSTGRES_PASSWORD` is applied only when the database volume is first initialised. Changing it in
  `.env` afterwards leaves the volume on the old password and `api` crash-loops with
  `asyncpg.exceptions.InvalidPasswordError`. Either match the value the volume was created with, or
  reset the volume deliberately with `docker compose down --volumes` (destroys demo data).
- Update `STATE.md` with verified evidence and remaining boundaries before handoff.
