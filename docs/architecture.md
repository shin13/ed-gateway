# ED Gateway MVP Architecture

## Request flow

`Chainlit -> FastAPI -> InterviewOrchestrator -> ResponseExtractor -> Pydantic state -> SafetyGate -> QuestionPlanner or DraftGenerator -> repository -> PostgreSQL`

Chainlit is deliberately thin. It displays the research notice, owns only the browser-session ID, sends messages to the API, and renders returned content. No clinical rule is implemented in the web service.

`InterviewOrchestrator` coordinates a durable two-stage turn. It first persists the raw answer, then extracts and validates observations before atomically saving the resulting state snapshot, event, assistant response, and optional draft. This deliberately preserves the raw answer if a provider or parser fails between those stages. `ResponseExtractor` separates raw wording from normalized values and statement type. `SafetyGate` evaluates version-controlled rules against validated observations. `QuestionPlanner` selects one configured question without repeating answered fields. `DraftGenerator` deterministically renders all required sections and preserves structured provenance.

The repository protocol separates the application layer from SQLAlchemy. Unit and API tests use the in-memory adapter; Docker uses the PostgreSQL adapter. Session state is stored as JSONB while messages, events, and draft revisions remain separately queryable.

## Trust boundaries

Live LLM output is an extraction proposal, not an authority. Pydantic validation, deterministic safety rules, and deterministic draft rendering define the system behavior. Rule IDs are returned without hidden reasoning. The system does not store or expose chain-of-thought.

Warning-sign detection runs in two layers. A deterministic sweep matches version-controlled Traditional Chinese phrases and always runs, with no provider dependency. Alongside it, the per-turn provider call screens the same categories semantically so a warning stated in another language is still detected. Provider proposals are whitelist-validated against the configured categories and are add-only: they may flag a category the deterministic sweep missed, never clear or downgrade one it found. `SafetyGate` consumes the merged observations and cannot tell which layer produced an entry, so escalation policy stays deterministic. A failed provider call degrades to deterministic-only screening for that turn and records the unscreened answer in the draft's nurse review points rather than raising an urgent prompt.

## Extension seams

Future EHR retrieval, authenticated users, approved device measurements, and a patient simulator can attach through adapters without changing the interview state model. They are intentionally absent from the MVP.
