# ED Gateway

ED Gateway is a runnable research MVP for structured emergency-department intake and nurse-review documentation. It collects synthetic patient or caregiver statements, applies a version-controlled warning-sign screen, preserves provenance, and produces a deterministic Markdown draft backed by structured JSON and an append-only event trail.

It is not a medical device, diagnosis system, treatment recommender, or autonomous triage system. It never assigns a formal TTAS level. All output requires review by a triage nurse.

## Architecture

- `web`: Chainlit adapter at `http://127.0.0.1:8000`. It creates sessions, forwards one answer at a time, and renders the draft plus a side-panel JSON view.
- `api`: FastAPI at `http://127.0.0.1:8001`. It owns extraction, state transitions, safety rules, question selection, persistence, and draft generation. OpenAPI is at `/docs`.
- `db`: PostgreSQL 16 on the internal Compose network with a named volume.

The domain core has no database dependency. `mock` mode is deterministic and offline; `openai_compatible` may assist extraction, while validated Pydantic state and deterministic safety rules remain authoritative.

## Start

Docker Compose is the supported full-system path. Python and Node.js are not required on the host.

```bash
cp .env.example .env
# Replace POSTGRES_PASSWORD in .env. Keep LLM_PROVIDER=mock for the offline demo.
docker compose up --build -d
docker compose ps
```

Open `http://127.0.0.1:8000`. Use synthetic demonstration data only.

The API liveness and readiness endpoints are:

```bash
curl -fsS http://127.0.0.1:8001/health/live
curl -fsS http://127.0.0.1:8001/health/ready
```

## Stop and inspect

```bash
docker compose logs --no-log-prefix api web db
docker compose down
```

Application logs intentionally do not include raw interview messages.

## Tests and quality gates

For local development with `uv`:

```bash
UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv sync --dev
UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run pytest
UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run ruff check .
UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run mypy
```

With the Compose stack healthy, run the live smoke test:

```bash
ED_GATEWAY_BASE_URL=http://127.0.0.1:8001 \
UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run pytest -m smoke
```

For manual validation and a feedback template, use the [synthetic live-validation checklist](docs/live-validation-checklist.md). Keep mock-functional, live-provider, clinical, and production evidence explicitly separate.

## Migrations

The API startup command runs `alembic upgrade head` after PostgreSQL becomes healthy. Manual commands:

```bash
docker compose run --rm api alembic current
docker compose run --rm api alembic upgrade head
```

## Database reset

This permanently removes local demonstration sessions and drafts. Stop first and use only when that deletion is intended:

```bash
docker compose down --volumes
```

The named volume otherwise survives application-container restarts.

## LLM providers

- `LLM_PROVIDER=mock`: no key or network required; used by automated tests.
- `LLM_PROVIDER=openai_compatible`: requires `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`. Startup configuration validation fails when any is missing.

Only the API container receives `DATABASE_URL` and `LLM_API_KEY`. The web container receives only `API_BASE_URL` and non-secret UI settings. Never commit `.env` or real patient data.

## Safety and privacy limits

See [source authority](docs/source-authority.md), [open clinical decisions](docs/open-clinical-decisions.md), [architecture](docs/architecture.md), and [post-MVP privacy requirements](docs/privacy-and-production-gaps.md). The configured warning rules are explicitly a clinical-review draft and must not be used in production without institutional governance and validation.
