# Multilingual Safety Detection Design

Status: approved design, not yet implemented. Approved 2026-09-17.

## Problem

The 12 warning-sign categories are detected only by matching hardcoded Traditional
Chinese phrases. `ResponseExtractor._detect_current_safety()` scans each clause of every
answer against `SAFETY_CONCEPTS` in `src/ed_gateway/application/extractor.py`, and that
dictionary contains no non-Chinese terms. A respondent who reports a warning sign in any
other language is not detected, and no provider setting changes that: this cross-field
sweep never calls the LLM at all.

Switching `LLM_PROVIDER` to `openai_compatible` does not close the gap. The live provider
is consulted once per turn, for the single field currently being asked, and the prompt in
`src/ed_gateway/llm/openai_compatible.py` explicitly frames the input as Traditional
Chinese. A warning sign mentioned incidentally, while answering some unrelated question,
reaches only the keyword sweep.

Goal: a warning sign stated in any language is detected, without weakening the
deterministic guarantees the project already depends on.

## Binding constraints

These come from `CLAUDE.md` and remain in force. The design is shaped around them rather
than around convenience.

- Live LLM output is a validated proposal. Deterministic safety rules stay authoritative.
- The 12 categories live in versioned configuration and stay labelled a clinical-review draft.
- A positive configured warning stops ordinary questions and requests immediate nurse review.
- Verbatim text stays separate from normalized values, with provenance retained.

## Decisions

1. **The LLM is a detector, never the decision-maker.** It may propose that a category is
   present. The rule that turns "category present" into "stop questioning, escalate to a
   nurse" stays in `config/safety-rules.yaml` and `SafetyGate`, which this design does not
   touch.
2. **Asymmetric trust.** An LLM proposal may only add a positive detection. It can never
   clear, deny, or downgrade a detection the keyword layer already made. A wrong or evasive
   model costs at most a redundant flag; it cannot suppress a warning.
3. **One LLM call per turn, not two.** The existing per-turn call is extended to also
   report other categories it noticed, rather than adding a second dedicated call. Latency
   and cost stay flat; the validation path stays single.
4. **A failed LLM call degrades quietly (option B1).** A provider error does not raise the
   urgent "call a nurse now" banner, because a network fault carries no clinical signal and
   a false urgent screen has its own on-site cost. Instead the turn completes normally on
   the keyword layer, and the draft carries a note asking the nurse to re-read that answer
   by hand.

## Architecture

Two independent detection layers feed one merged observation set. `SafetyGate` reads the
merged set and cannot tell which layer produced an entry.

**Layer 1 — deterministic keyword sweep (unchanged).** `_detect_current_safety()` keeps
scanning every clause of every answer against `SAFETY_CONCEPTS`. It costs nothing, adds no
latency, needs no provider, and never fails. It remains the floor under the whole feature:
if the LLM is misconfigured, unreachable, or wrong, Chinese-language coverage is exactly
what it is today.

**Layer 2 — LLM semantic screen (new).** The per-turn provider call also receives short
English descriptions of the other categories and returns the ones it judges currently and
positively present in the answer, in whatever language the answer was given.

```
respondent answer (any language)
  → Layer 1: keyword sweep over all 12 categories        (deterministic, always runs)
  → local extraction for the field being asked            (deterministic)
  → one LLM call: { classification for this field, other categories noticed }
      ├─ success → validate each proposal → add-only merge
      └─ failure → SafetyScanDegraded → keep local results, record a nurse-review note
  → SafetyGate.evaluate()                                 (unchanged, deterministic)
```

## Component changes

### 1. `config/safety-rules.yaml`

Each of the 12 rules gains `detection_concepts_en`: a list of short English clinical
descriptions of that category. The field name records what the values are (English text);
their purpose is to let the model generalize semantically to any language, not to match
English literally.

The Chinese phrase lists in `SAFETY_CONCEPTS` are not moved into config by this change.
Doing so would rewrite the deterministic layer at the same time as adding the probabilistic
one, and the two failure modes should not be entangled in a single change. The gap is real
and stays recorded in `docs/open-clinical-decisions.md`.

### 2. `SafetyRuleDefinition` in `src/ed_gateway/application/configuration.py`

Add `detection_concepts_en: list[str]`. The model is `extra="forbid"`, so the config and the
schema must be updated together; startup validation then fails loudly on a mismatch, which
is the intended behaviour.

### 3. `src/ed_gateway/bootstrap.py`

`create_orchestrator` builds `{observation_field: detection_concepts_en}` from
`config.safety_rules` and passes it to `ResponseExtractor`. This replaces the positional
construction at `bootstrap.py:40`.

### 4. `ResponseExtractor` in `src/ed_gateway/application/extractor.py`

- Constructor takes the category description mapping alongside the LLM client.
- `extract()` passes those descriptions to the provider through the existing
  `context: dict[str, Any]` parameter of `LLMClient.extract()`. The `LLMClient` protocol
  stays provider-neutral and learns nothing about the 12 categories.
- A new private method validates a proposal's `other_safety_categories` list:
  - every entry must be a known `safety.*` field from the injected mapping — an unknown or
    invented category name is discarded, the same whitelist discipline applied to
    `respondent.type` in commit `2eee3cc`;
  - `expected_field` is skipped if the model includes it, because that field is already
    handled by the existing single-field classification branch;
  - a category already present in this turn's observations is not duplicated.
- Accepted entries become `Observation(status=CONFIRMED,
  normalized_value={"present": True, "detected_by": "llm_semantic_screen"},
  ai_normalized=True, requires_human_confirmation=True)`. `present` is the key `SafetyGate`
  already reads; `detected_by` records which layer produced the detection, mirroring the
  existing `{"present": True, "concepts": [...]}` shape from the keyword sweep.
  `requires_human_confirmation` is set because these detections bypass the deterministic
  layer entirely and are the least certain input the system produces.

### 5. `OpenAICompatibleClient` in `src/ed_gateway/llm/openai_compatible.py`

- Drop the "Traditional Chinese" framing from the prompt; state that the answer may be in
  any language and must be interpreted semantically.
- Add a prompt section listing the other categories to check, built from `context`, and add
  `other_safety_categories` to the requested JSON keys. The client holds no category list of
  its own; an absent or empty context entry simply omits that prompt section.

### 6. Failure handling

A new `SafetyScanDegraded` exception carries the observations already computed locally.
`extract()` wraps only the `self._llm.extract(...)` call and raises it on any provider
exception. `InterviewOrchestrator.handle_message` catches it, proceeds with the carried
observations, and appends the answer to a new
`InterviewState.safety_scan_degraded: list[str]`, following the existing
`contradictions: list[str]` idiom.

This also closes a pre-existing defect: `orchestrator.py:79` currently has no exception
handling around the extractor call, so today any provider timeout, connection failure, or
non-JSON response after retry exhaustion crashes the whole turn with a 500. That path gets
its own regression test.

### 7. `DraftGenerator._review_points()` in `src/ed_gateway/application/drafts.py`

When `state.safety_scan_degraded` is non-empty, append a line naming the count and quoting
each affected answer, asking the nurse to re-read them for warning signs. The draft template
and its placeholder set are unchanged; only the rendered content of 【護理師覆核重點】 grows.

## Testing plan

Written test-first, in the style of the existing suite.

- `tests/unit/test_extractor.py`
  - a proposal listing another category adds a `CONFIRMED` observation for it, with
    `requires_human_confirmation` set;
  - an unknown or invented category name is discarded;
  - a category the keyword sweep already found in the same turn is not duplicated;
  - `expected_field` appearing in the list does not produce a second observation;
  - a provider that raises causes `SafetyScanDegraded` carrying the local observations,
    not an unhandled exception.
- `tests/unit/test_models.py` — `safety_scan_degraded` accumulates across turns.
- `tests/unit/test_drafts.py` — the review-points note appears when degraded and the normal
  wording is unchanged otherwise.
- `tests/unit/test_configuration.py` — the new config field is loaded and validated for all
  12 rules.
- `tests/unit/test_orchestrator.py` (new file) — a turn whose provider raises still
  completes, records the answer in `safety_scan_degraded`, and keeps the keyword-layer
  observations. The orchestrator is constructed directly, the way `bootstrap.py` does it.
  An HTTP-level variant is possible but needs `ed_gateway.bootstrap.create_llm_client`
  monkeypatched: `create_app` takes `settings` and `repository` only, and the route closes
  over the orchestrator built inside it, so `app.state.orchestrator` cannot be swapped after
  the fact.
- Live verification against the real provider, as done for commit `2eee3cc`: send a
  non-Chinese warning-sign statement while a different field is being asked, and confirm the
  category is detected, flagged for human confirmation, and that existing Chinese-language
  behaviour is unaffected.

Mock mode needs no change. `MockLLMClient.extract()` returns no `classification`, so every
proposal path short-circuits exactly as it does today, and it never raises, so the degraded
path never triggers offline.

## Residual scope

- The English descriptions are a working translation of the existing Chinese phrase lists and
  have had no clinical review. They are a clinical-review draft on the same footing as
  `clinical-review-draft-v1`. Implementation must add them to
  `docs/open-clinical-decisions.md` in the same change that introduces them, so no reviewer
  reads that file and concludes the wording was approved.
- Languages are covered only as well as the configured model covers them. This design adds no
  per-language evaluation, and none has been run.
- The Chinese phrase lists remain hardcoded in `extractor.py` rather than versioned in
  `config/`, which still contradicts the architecture note in `CLAUDE.md`. Unchanged by this
  design and still open.
- Other non-safety fields still accept whatever shape a provider proposes, apart from
  `respondent.type`. No crash is known there, but no exhaustive live testing has been done.
