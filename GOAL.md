# Goal: Build the ED Gateway MVP

Build a complete, runnable MVP of `ed-gateway`, a general-purpose AI-assisted
emergency-department intake and documentation system.

Do not stop after planning or scaffolding. Implement and verify the complete
vertical slice from the Chainlit dialogue starter, through multi-turn symptom
collection, to generation and persistence of a nurse-review draft.
## 1. Authoritative locations
### Whole project and research-material root

`/Users/shin/Downloads/20260629_廖珍娟老師台大新竹分院急診林怡芬護理長研究急診檢傷分流`

This directory contains the project discussion, nursing documents, clinical
references, prompt drafts, PDFs, DOCX files, and research papers. Treat it as
read-only unless the user explicitly requests a documentation change.

Important references include:

- `1_INSTRUCTIONS_貼入指令欄_v2.1.md`
- `2_KNOWLEDGE_急診前哨_警訊與範例.md`
- `急診前哨_system_prompt_v2.md`
- `胸痛.docx`
- `頭暈.docx`
- `發燒.docx`
- `下背痛.docx`
- `reference/arxiv-2506.04032.pdf`
- the TTAS and workflow PDFs in that directory

The `ed-gateway` entry in the research root is a symbolic link. Do not create a
second copy of the repository there.
### Authoritative code repository

`/Users/shin/Projects/ed-gateway`

This is the only authoritative codebase. Create all source code, tests,
configuration templates, migrations, Docker files, engineering documentation,
and Git commits here.

Before editing:

1. Run `git rev-parse --show-toplevel`.
2. Confirm the result is `/Users/shin/Projects/ed-gateway`.
3. Inspect Git status and preserve unrelated user changes.
4. Do not initialize or modify Git in the research-material root.
5. Do not copy the codebase into the research-material root.
## 2. Product mission

ED Gateway assists conscious, conversational emergency-department patients or
their caregivers in providing initial information before a nurse completes
formal triage.

The MVP must:

1. Start a structured conversation in Traditional Chinese.
2. Identify whether the respondent is the patient or a caregiver.
3. Collect age and the chief complaint in the respondent's own words.
4. Check configured urgent warning signs throughout the interview.
5. Collect symptoms through one general framework across different complaints.
6. Preserve verbatim statements and normalized structured data separately.
7. Generate a structured nursing triage note draft.
8. Persist sessions, messages, observations, safety events, and drafts.
9. Let a nurse or evaluator review the resulting draft.

This is a research and demonstration system. It is not a production medical
device or an autonomous triage system.
## 3. Binding clinical boundary

The AI may collect and clarify information, normalize answers into a structured
schema, detect configured warning-sign conditions, stop normal questioning for
immediate nurse review, and generate a nurse-review draft.

The AI must never assign or display formal TTAS/triage levels, diagnose,
speculate about diagnoses, recommend medication or treatment, promise that
waiting is safe, estimate missing measurements, present AI inference as a
patient statement, automatically submit a final hospital record, or expose
hidden chain-of-thought.

The nurse and hospital-approved system remain responsible for formal triage,
clinical decisions, and the final medical record.

Every ordinary draft and urgent-warning summary must end with:

> 此為護理紀錄草稿，須由檢傷護理師確認後方可使用。
## 4. Reference authority

Read the supplied materials before implementing clinical behavior. Use this
authority order:

1. This goal defines product and engineering scope.
2. `1_INSTRUCTIONS_貼入指令欄_v2.1.md` is the candidate source for dialogue
   order and safety boundaries.
3. `2_KNOWLEDGE_急診前哨_警訊與範例.md` supplies wording and examples.
4. The four chief-complaint DOCX files are nursing examples, fixtures, and
   acceptance material. They are not four independent application flows.
5. `reference/arxiv-2506.04032.pdf` provides architecture and evaluation ideas,
   not authority for diagnosis, treatment, or autonomous triage.
6. TTAS PDFs are reference only. Do not implement formal TTAS scoring.

Known conflict: an older workflow mentions a 4.5-hour neurological threshold,
while the newer instructions remove it. Do not use that window as an escalation
condition. Record onset or last-known-normal time, but route configured current
neurological warning signs for nurse review regardless of that time.

Create `docs/source-authority.md` with this ordering and
`docs/open-clinical-decisions.md` for unresolved issues. Do not silently resolve
new clinical conflicts.
## 5. Required architecture

Use Docker Compose with three services.
### `web`

- Chainlit frontend and conversational adapter.
- Use `on_chat_start` to create a backend session and show the introduction.
- Use `on_message` to send each answer to the API.
- Keep clinical rules and interview logic out of this service.
- Call the API through the internal Docker network.
- Run with `chainlit run <app> -h --host 0.0.0.0`.
- Expose locally at `http://127.0.0.1:8000`.
### `api`

- FastAPI backend.
- Own orchestration, schemas, rule evaluation, persistence, question planning,
  LLM integration, and draft generation.
- Expose locally at `http://127.0.0.1:8001`.
- Provide liveness and readiness endpoints.
### `db`

- PostgreSQL using a pinned official major-version image.
- Use a named Docker volume.
- Keep the database internal to the Compose network.
- Manage schema changes with Alembic.

Do not add Redis, Celery, a vector database, Kubernetes, or background workers
unless a demonstrated MVP requirement makes one necessary.

Use Python 3.12, `uv`, Chainlit, FastAPI, Pydantic v2, pydantic-settings,
SQLAlchemy 2.x with async PostgreSQL access, Alembic, HTTPX, pytest, and Ruff.
Commit `uv.lock` and verify current Chainlit compatibility before pinning.
## 6. Environment and provider configuration

All runtime configuration must come from environment variables. Use a
root-level `.env` for local development and Docker Compose. Commit
`.env.example`, never `.env`.

Add `.env` to `.gitignore`. Never commit API keys, passwords, tokens, or real
patient information.

Use `pydantic-settings` to define one typed settings entry point. Load and
validate settings at application startup. Do not scatter `os.getenv()` calls
through domain or application code.
### `.env.example`

Include at least:

```dotenv
APP_ENV=development
APP_NAME=ED Gateway
LOG_LEVEL=INFO
DEMO_MODE=true

LLM_PROVIDER=mock
LLM_MODEL=
LLM_BASE_URL=
LLM_API_KEY=
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=1
LLM_TEMPERATURE=0

POSTGRES_DB=ed_gateway
POSTGRES_USER=ed_gateway
POSTGRES_PASSWORD=replace-with-local-secret
DATABASE_URL=postgresql+asyncpg://ed_gateway:replace-with-local-secret@db:5432/ed_gateway

API_HOST=0.0.0.0
API_PORT=8001
API_BASE_URL=http://api:8001

CHAINLIT_HOST=0.0.0.0
CHAINLIT_PORT=8000
```

Support these LLM providers:

- `mock`: deterministic, offline, and used by automated tests;
- `openai_compatible`: configured with `LLM_BASE_URL`, `LLM_API_KEY`, and
  `LLM_MODEL`.

Do not hardcode a provider URL, model name, or API key. Live-provider readiness
must fail clearly when required settings are missing. Mock mode must run without
an API key.

Only `api` may receive `LLM_API_KEY` and `DATABASE_URL`. `web` receives only
Chainlit settings and `API_BASE_URL`. `db` receives only PostgreSQL settings.
Use explicit Compose environment allowlists instead of injecting the complete
`.env` into every container.

Redact secrets from settings representations, logs, diagnostics, and errors.
## 7. Backend components
### `InterviewSessionManager`

Create, retrieve, update, finish, stop, and escalate interview sessions.
### `InterviewOrchestrator`

For each user answer:

1. Persist the raw message.
2. Extract structured observations.
3. Merge validated observations into interview state.
4. Run the safety gate.
5. Escalate, select the next question, or generate a draft.
6. Persist the event and state snapshot.
7. Return one patient-facing response.

Keep business rules in their own components rather than accumulating them in
the orchestrator.
### `ResponseExtractor`

Convert free text into validated Pydantic structures. Distinguish:

- present symptoms;
- explicitly denied symptoms;
- past medical history;
- family history;
- hypothetical questions;
- patient and caregiver statements;
- device and clinician measurements;
- unclear information requiring clarification.

Do not use keyword matching as the sole interpretation method.
### `SafetyGate`

Evaluate version-controlled deterministic rules against structured observations
and accumulated state. The first rule configuration should represent the 12
warning-sign categories in the reference instructions and be labeled as a
clinical-review draft.

If a rule triggers:

- change the session phase to `ESCALATED`;
- stop ordinary questioning;
- preserve the triggering verbatim statement;
- produce an urgent-warning summary;
- list obtained and missing critical information;
- request immediate nurse review;
- never produce a diagnosis or formal triage level.

For safety-critical ambiguity, ask one direct clarification when safe;
otherwise conservatively escalate.
### `QuestionPlanner`

Select one next question using this priority:

1. unresolved immediate safety concerns;
2. respondent identity and age;
3. chief complaint in the respondent's own words;
4. required safety-screen fields;
5. missing general symptom fields;
6. applicable context rules;
7. review and completion;
8. draft generation.

Avoid repeated questions. Accept 「不知道」, 「跳過」, and refusal as explicit
states. Ask for clarification when answers conflict. Permit early completion
and generate a partial draft with missing fields identified.
### `DraftGenerator`

Generate the canonical Markdown draft deterministically from structured state.
LLM-assisted wording is optional, but every statement must be traceable to the
structured state. The deterministic structured draft remains authoritative.
### Persistence and LLM adapters

Keep persistence interfaces separate from SQLAlchemy implementations. Define a
small provider-neutral LLM interface with deterministic test doubles. Domain
tests must not require PostgreSQL or a live model.
## 8. Interview schema

Use Pydantic models as runtime authority. Store validated state snapshots in
PostgreSQL JSONB and maintain an append-only event trail.
### Constrained values

- Interview phase: `STARTER`, `RESPONDENT`, `AGE`, `SAFETY_SCREEN`,
  `SYMPTOM_COLLECTION`, `REVIEW`, `DRAFT_READY`, `ESCALATED`, `STOPPED`.
- Information source: `PATIENT_STATEMENT`, `CAREGIVER_STATEMENT`,
  `DEVICE_MEASUREMENT`, `CLINICIAN_MEASUREMENT`, `AI_NORMALIZATION`.
- Field status: `NOT_OBTAINED`, `CONFIRMED`, `DENIED`, `UNKNOWN`, `DECLINED`,
  `NOT_APPLICABLE`, `NEEDS_CLARIFICATION`.

Each observation must include a stable field key, verbatim text, normalized
value, source, status, timestamp, whether AI normalization was used, and whether
human confirmation is needed.

The general symptom model must support chief complaint, onset, location,
quality, severity and assessment method, duration, timing, sudden or gradual
onset, constant or intermittent course, aggravating factors, relieving factors,
radiation, associated symptoms, recent change, trauma context, and functional
impact.

Also support respondent type, age, interaction mode, answer language, arrival
source, medical history, medications, allergies, TOCC/exposure information,
vital signs with source and measurement time, and missing or contradictory data.

Always retain the verbatim chief complaint when a normalized label exists.
## 9. Version-controlled configuration

Create and validate at startup:

- `config/interview-schema.yaml`
- `config/question-catalog.yaml`
- `config/safety-rules.yaml`
- `config/context-rules.yaml`
- `config/nurse-draft-template.md`

Question definitions should include ID, target field, Traditional Chinese
wording, answer type, required status, applicable phase, applicability rules,
safety relevance, and alternate clarification wording.

Chief-complaint material may add priorities and follow-up hints. It must not
select a separate hardcoded interview flow.
## 10. Required dialogue behavior
### Dialogue starter

On a new Chainlit chat, create a backend session and show a concise Traditional
Chinese introduction stating that ED Gateway collects and organizes information
for the triage nurse, does not diagnose or determine treatment order, and that
the respondent must immediately notify on-site staff if the patient worsens.

Then ask only:

> 現在操作的是病人本人，還是家屬或陪同者？
### Symptom collection

After respondent type, age, and the configured safety sequence, ask:

> 請用自己的話告訴我，今天主要是哪裡不舒服？

Collect symptoms dynamically through the shared schema. Ask one question per
turn. Chest discomfort, dizziness, fever, and lower-back pain must all use the
same engine.
### Completion and escalation

Provide a visible Chainlit action such as 「完成並產生草稿」. Early completion
produces a partial draft with missing data marked. Escalation must display a
prominent request for immediate nurse assistance and stop ordinary questioning.
Provide a clearly labeled way to start a new synthetic demo session.
## 11. Nurse draft

Always render these sections, using 「未取得」 where appropriate: 【互動模式】,
【操作者】, 【警訊與處置】, 【基本資料】, 【到院資訊】, 【TOCC／暴露資料】,
【主訴】, 【症狀時間軸】, 【生命徵象與意識】, 【疼痛】, 【功能狀態】,
【既往史與用藥過敏】, 【缺失與矛盾資料】, and 【護理師覆核重點】.
【檢傷級數】 must always display 「待檢傷護理師／院方系統確認」.

End with the required disclaimer. In Chainlit, show the human-readable Markdown
draft and an expandable structured JSON view for developer verification.
## 12. API contract

Implement at least:

- `POST /api/v1/interview-sessions`
- `POST /api/v1/interview-sessions/{session_id}/messages`
- `POST /api/v1/interview-sessions/{session_id}/finish`
- `GET /api/v1/interview-sessions/{session_id}`
- `GET /api/v1/interview-sessions/{session_id}/draft`
- `GET /health/live`
- `GET /health/ready`

Turn responses should contain session ID, phase, patient-facing message, next
question ID when applicable, safety status, triggered rule IDs without hidden
reasoning, completion status, and the draft when generated.

Publish FastAPI OpenAPI documentation.
## 13. Persistence

Persist at least:

- `interview_sessions`: UUID, phase, respondent type, mode, state JSONB, rule
  version, and timestamps;
- `interview_events`: append-only state and safety events;
- `messages`: sequence, role, raw content, source, and timestamp;
- `drafts`: revision, structured JSON, rendered Markdown, and timestamp.

Use UTC in persistence and clearly render user-facing times.
## 14. Privacy and demo safety

- Display a visible 「研究展示用途」 notice.
- Use synthetic demonstration data only.
- Do not request national ID, complete address, financial, or insurance data.
- Do not require a real patient name.
- Do not log raw messages to container stdout.
- Bind host-exposed services to localhost.
- Document authentication, hospital SSO, encryption-key management, retention,
  and production privacy review as post-MVP requirements.
## 15. Docker and developer experience

`docker compose up --build` must start the complete system without requiring
locally installed Python or Node.js.

Requirements:

- API waits for PostgreSQL readiness.
- Alembic migrations run in a controlled startup step.
- Chainlit waits for API readiness.
- Database, API, and web have health checks.
- Use a named database volume.
- Add `.dockerignore`, `.gitignore`, and `.env.example`.
- Run containers as non-root where practical.
- Support clean shutdown.
- Document startup, shutdown, logs, tests, migrations, and database reset.
## 16. Testing

Use the mock LLM in automated tests.
### Unit tests

Cover schema and settings validation, source/status handling, state transitions,
observation merging, question priority, skip/unknown/refusal, repeated-question
prevention, deterministic draft rendering, and safety-rule evaluation.
### Safety interpretation tests

Cover present symptoms, negation, past history, family history, hypothetical
questions, caregiver statements, contradictory answers, and unclear answers.

For example, 「我爸爸中風過」 must not be treated as the patient's current
neurological symptom.
### Integration tests

Cover session creation, a normal complete interview, partial completion, urgent
escalation, PostgreSQL persistence, session retrieval, and draft retrieval.
### Reference-derived fixtures

Create synthetic chest discomfort, dizziness, fever, and lower-back-pain
fixtures. All must use the same orchestrator and schema while producing relevant
follow-up questions.
### Compose smoke test

Verify all services become healthy, Chainlit responds, the API creates a
session, and a multi-turn exchange generates a draft.
## 17. Suggested repository structure

Use a `src/ed_gateway` package with `api`, `chainlit_ui`, `domain`,
`application`, `infrastructure`, and `llm` modules. Keep versioned configuration
under `config`, Alembic files under `migrations`, tests and fixtures under
`tests`, and engineering records under `docs`. Root files must include
`pyproject.toml`, `uv.lock`, `Dockerfile`, `docker-compose.yml`, `.env.example`,
`.gitignore`, `.dockerignore`, and `README.md`.

Prefer one build image with separate Compose commands for `api` and `web` when
that keeps dependencies and development simple.
## 18. Non-goals

Do not implement formal TTAS scoring, differential diagnosis, treatment or
medication advice, production EHR integration, automatic final-record
submission, medical-device integration, production authentication, voice
transcription, multiple LLM agents, guideline RAG, vector search, mass-casualty
flows, or production deployment claims.

Design interfaces so EHR retrieval, device input, authentication, and a patient
simulator can be added later without rewriting the domain model.
## 19. Acceptance criteria

The MVP is complete only when all conditions are observed:

1. `docker compose up --build` starts healthy `web`, `api`, and `db` services.
2. `http://127.0.0.1:8000` shows the Traditional Chinese research-demo UI.
3. Starting a chat creates and persists a session.
4. The first message contains the safety framing and asks respondent type.
5. A normal synthetic conversation reaches symptom collection and creates a
   nurse-review draft.
6. The four reference complaints use one engine and schema.
7. Drafts preserve verbatim text, normalized data, source labels, missing data,
   and contradictions.
8. An urgent-warning fixture stops normal questioning and creates an urgent
   summary.
9. No output assigns a formal triage level, diagnosis, medication, or treatment.
10. Sessions and drafts persist after application-container restart while the
    database volume is retained.
11. Automated tests pass in mock-provider mode.
12. Ruff and configured type checks pass.
13. README commands have been executed and verified.
14. The final handoff reports architecture, safety boundaries, commands run,
    test and Compose results, limitations, and unresolved clinical decisions.

Do not claim completion from generated files alone. Run tests, start the Compose
stack, exercise the normal and escalation paths, and report observed results.
