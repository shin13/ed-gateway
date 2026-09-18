# Multilingual Safety Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect the 12 warning-sign categories when a respondent states them in any language, without weakening the deterministic safety rules.

**Architecture:** Two detection layers feed one observation set. The existing Chinese keyword sweep stays untouched as the floor. The per-turn LLM call is extended to also report other categories it noticed; those proposals are whitelist-validated and can only *add* a positive detection, never clear one. `SafetyGate` is unchanged and cannot tell which layer produced an entry. A provider failure degrades to a nurse-review note in the draft instead of raising the urgent banner.

**Tech Stack:** Python 3.12, Pydantic v2, pytest (asyncio auto mode), Ruff, mypy strict, YAML config.

**Spec:** `docs/multilingual-safety-detection-design.md`

## Global Constraints

- Live LLM output is a validated proposal; deterministic safety rules and drafts remain authoritative.
- The 12 categories stay in versioned configuration, labelled a clinical-review draft.
- LLM proposals may only add a positive detection. Never clear, deny, or downgrade an existing one.
- Traditional Chinese for patient-facing text; English for code and engineering docs.
- `SafetyGate` and `config/safety-rules.yaml` rule IDs / `observation_field` values must not change.
- Keep it simple: smallest mechanism that does the job, no hidden side effects.
- Quality gates for every task: `uv run pytest`, `uv run ruff check .`, `uv run mypy`, `git diff --check`.
- Prefix `uv` commands with `UV_CACHE_DIR=/tmp/ed-gateway-uv-cache`.

---

### Task 1: Versioned English concept descriptions

Puts language-neutral semantic descriptions of the 12 categories into versioned config, and records that the wording is an unreviewed translation.

**Files:**
- Modify: `config/safety-rules.yaml`
- Modify: `src/ed_gateway/application/configuration.py:26-33`
- Modify: `docs/open-clinical-decisions.md`
- Test: `tests/unit/test_configuration.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `SafetyRuleDefinition.detection_concepts_en: list[str]`, populated for all 12 rules.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_configuration.py`:

```python
def test_every_safety_rule_has_english_detection_concepts() -> None:
    config = load_clinical_config(Path(__file__).parents[2] / "config")

    for rule in config.safety_rules:
        assert rule.detection_concepts_en, f"{rule.id} has no English detection concepts"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run pytest tests/unit/test_configuration.py::test_every_safety_rule_has_english_detection_concepts -v`
Expected: FAIL with `AttributeError: 'SafetyRuleDefinition' object has no attribute 'detection_concepts_en'`

- [ ] **Step 3: Add the field to the config schema**

In `src/ed_gateway/application/configuration.py`, add one field to `SafetyRuleDefinition` (it is `extra="forbid"`, so config and schema must move together):

```python
class SafetyRuleDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    category: str
    observation_field: str
    trigger_statuses: list[str] = Field(default_factory=lambda: ["CONFIRMED"])
    clinical_review_status: str
    detection_concepts_en: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Add the descriptions to `config/safety-rules.yaml`**

Add a `detection_concepts_en` list to each of the 12 rules. Keep every existing key and value exactly as it is; only add.

```yaml
  - id: WARN-CARDIOVASCULAR
    category: 心血管／胸痛
    observation_field: safety.cardiovascular
    clinical_review_status: draft
    detection_concepts_en:
      - chest pain
      - chest tightness or chest pressure
  - id: WARN-NEUROLOGICAL
    category: 神經
    observation_field: safety.neurological
    clinical_review_status: draft
    detection_concepts_en:
      - facial drooping
      - weakness or numbness on one side of the body
      - slurred or unclear speech
      - sudden vision loss or double vision
      - sudden loss of balance, unable to stand
      - worst headache of their life
      - seizure or convulsions
      - unresponsive, cannot be woken
      - fainted or lost consciousness
  - id: WARN-RESPIRATORY
    category: 呼吸
    observation_field: safety.respiratory
    clinical_review_status: draft
    detection_concepts_en:
      - too short of breath to speak
      - blue or purple lips
      - difficulty breathing
      - swollen throat or blocked airway
  - id: WARN-CIRCULATION
    category: 循環
    observation_field: safety.circulation
    clinical_review_status: draft
    detection_concepts_en:
      - about to faint
      - vision going dark or blacking out
      - cold clammy skin
      - pale complexion
      - palpitations with weakness
  - id: WARN-BLEEDING
    category: 出血
    observation_field: safety.bleeding
    clinical_review_status: draft
    detection_concepts_en:
      - bleeding that will not stop
      - vomiting blood
      - black tarry stools
      - large amount of blood in stool
      - heavy vaginal bleeding
  - id: WARN-ALLERGY
    category: 過敏
    observation_field: safety.allergy
    clinical_review_status: draft
    detection_concepts_en:
      - hives or rash over the whole body
      - swollen lips
      - swollen throat
      - severe allergic reaction
  - id: WARN-INFECTION-TEMPERATURE
    category: 感染與體溫
    observation_field: safety.infection_temperature
    clinical_review_status: draft
    detection_concepts_en:
      - fever together with confusion or altered consciousness
      - fever together with severe shortness of breath
  - id: WARN-SEVERE-PAIN
    category: 劇烈疼痛
    observation_field: safety.severe_pain
    clinical_review_status: draft
    detection_concepts_en:
      - pain rated ten out of ten
      - extreme or unbearable pain
      - sudden constant abdominal pain
  - id: WARN-TRAUMA
    category: 高風險外傷機轉
    observation_field: safety.trauma
    clinical_review_status: draft
    detection_concepts_en:
      - thrown or ejected from a vehicle
      - vehicle rollover
      - gunshot wound
      - stab or penetrating wound
      - fall from height
      - trapped or pinned
  - id: WARN-HYPERTENSIVE
    category: 高血壓合併症狀
    observation_field: safety.hypertensive
    clinical_review_status: draft
    detection_concepts_en:
      - systolic blood pressure around two hundred
  - id: WARN-MENTAL-HEALTH
    category: 心理健康
    observation_field: safety.mental_health
    clinical_review_status: draft
    detection_concepts_en:
      - wanting to die
      - thoughts of self-harm
      - thoughts of harming others
      - unable to calm down, in crisis
  - id: WARN-SELF-IDENTIFIED-DANGER
    category: 病人自述危險
    observation_field: safety.self_identified_danger
    clinical_review_status: draft
    detection_concepts_en:
      - feels about to collapse
      - feels they cannot hold on
      - says the situation is dangerous
```

- [ ] **Step 5: Record the unreviewed wording as an open clinical decision**

Append to `docs/open-clinical-decisions.md` as item 10:

```markdown
10. The English `detection_concepts_en` wording in `config/safety-rules.yaml` is a working
    translation of the Chinese phrase lists, used to let the language model recognise the 12
    categories in any language. It has had no clinical or bilingual review, carries the same
    `clinical-review-draft-v1` status as the Chinese lists, and no per-language detection
    evaluation has been run.
```

- [ ] **Step 6: Run the test and the quality gates**

Run: `UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run pytest && UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run ruff check . && UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run mypy`
Expected: all pass, 61 passed / 1 skipped or more.

- [ ] **Step 7: Commit**

```bash
git add config/safety-rules.yaml src/ed_gateway/application/configuration.py docs/open-clinical-decisions.md tests/unit/test_configuration.py
git commit -m "feat: version English concept descriptions for the 12 warning categories"
```

---

### Task 2: Extractor accepts, validates, and merges multilingual category proposals

The extractor's whole side of the feature: it forwards the descriptions to the provider and turns validated proposals into observations under add-only rules.

**Files:**
- Modify: `src/ed_gateway/application/extractor.py:138-220`
- Modify: `src/ed_gateway/bootstrap.py:40`
- Test: `tests/unit/test_extractor.py`

**Interfaces:**
- Consumes: `SafetyRuleDefinition.detection_concepts_en` from Task 1.
- Produces: `ResponseExtractor(llm, safety_categories: dict[str, list[str]])`; the provider is called with `context["safety_categories"]`; proposals may carry `other_safety_categories: list[str]`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_extractor.py`:

```python
SAFETY_CATEGORIES = {
    "safety.cardiovascular": ["chest pain"],
    "safety.neurological": ["weakness on one side of the body"],
}


class _ProposalLLM:
    def __init__(self, categories: object) -> None:
        self._categories = categories
        self.context: dict[str, object] = {}

    async def extract(self, *, text: str, expected_field: str, context: dict) -> dict:
        self.context = context
        return {
            "classification": "current",
            "normalized_value": None,
            "status": "NEEDS_CLARIFICATION",
            "other_safety_categories": self._categories,
        }


async def test_provider_categories_reach_the_llm_client(state) -> None:
    llm = _ProposalLLM([])
    await ResponseExtractor(llm, SAFETY_CATEGORIES).extract(
        text="hello",
        expected_field="symptom.onset",
        state=state,
    )
    assert llm.context["safety_categories"] == SAFETY_CATEGORIES


async def test_non_chinese_warning_is_detected_from_provider_proposal(state) -> None:
    observations = await ResponseExtractor(
        _ProposalLLM(["safety.neurological"]), SAFETY_CATEGORIES
    ).extract(
        text="my right arm went weak an hour ago",
        expected_field="symptom.onset",
        state=state,
    )
    warning = next(item for item in observations if item.field_key == "safety.neurological")
    assert warning.status == FieldStatus.CONFIRMED
    assert warning.normalized_value == {"present": True, "detected_by": "llm_semantic_screen"}
    assert warning.requires_human_confirmation is True
    assert warning.verbatim_text == "my right arm went weak an hour ago"


async def test_unknown_proposed_category_is_discarded(state) -> None:
    observations = await ResponseExtractor(
        _ProposalLLM(["safety.invented", 42]), SAFETY_CATEGORIES
    ).extract(
        text="my arm went weak",
        expected_field="symptom.onset",
        state=state,
    )
    assert not any(item.field_key == "safety.invented" for item in observations)


async def test_provider_does_not_duplicate_a_keyword_detection(state) -> None:
    observations = await ResponseExtractor(
        _ProposalLLM(["safety.neurological"]), SAFETY_CATEGORIES
    ).extract(
        text="我現在突然半邊無力",
        expected_field="symptom.onset",
        state=state,
    )
    neurological = [item for item in observations if item.field_key == "safety.neurological"]
    assert len(neurological) == 1
    assert neurological[0].normalized_value["present"] is True
    assert "concepts" in neurological[0].normalized_value


async def test_provider_does_not_add_a_second_observation_for_the_asked_field(state) -> None:
    observations = await ResponseExtractor(
        _ProposalLLM(["safety.cardiovascular"]), SAFETY_CATEGORIES
    ).extract(
        text="something feels off in my chest",
        expected_field="safety.cardiovascular",
        state=state,
    )
    assert len([item for item in observations if item.field_key == "safety.cardiovascular"]) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run pytest tests/unit/test_extractor.py -v -k "provider_categories or non_chinese or unknown_proposed or duplicate_a_keyword or second_observation"`
Expected: FAIL with `TypeError: ResponseExtractor() takes 2 positional arguments but 3 were given`

- [ ] **Step 3: Take the descriptions in the constructor and forward them**

In `src/ed_gateway/application/extractor.py`, change the constructor:

```python
    def __init__(self, llm: LLMClient, safety_categories: dict[str, list[str]] | None = None) -> None:
        self._llm = llm
        self._safety_categories = safety_categories or {}
```

Then in `extract()`, add `safety_categories` to the context passed to the provider:

```python
        proposal = await self._llm.extract(
            text=text,
            expected_field=expected_field,
            context={
                "respondent_type": state.respondent_type.value,
                "classification": classification,
                "safety_categories": self._safety_categories,
            },
        )
```

- [ ] **Step 4: Merge validated category proposals**

Still in `extract()`, immediately after the existing `provider_observation` block and before `return observations`:

```python
        observations.extend(
            self._proposed_safety_observations(
                proposal=proposal,
                text=text,
                expected_field=expected_field,
                source=source,
                observations=observations,
            )
        )
        return observations
```

Add this method to `ResponseExtractor`:

```python
    def _proposed_safety_observations(
        self,
        *,
        proposal: dict[str, Any],
        text: str,
        expected_field: str,
        source: InformationSource,
        observations: list[Observation],
    ) -> list[Observation]:
        """Add-only: a proposal may flag a category the keyword sweep missed, never clear one."""
        proposed = proposal.get("other_safety_categories")
        if not isinstance(proposed, list):
            return []
        seen = {item.field_key for item in observations} | {expected_field}
        additions: list[Observation] = []
        for field in proposed:
            if not isinstance(field, str) or field not in self._safety_categories or field in seen:
                continue
            seen.add(field)
            additions.append(
                Observation(
                    field_key=field,
                    verbatim_text=text,
                    normalized_value={"present": True, "detected_by": "llm_semantic_screen"},
                    source=source,
                    status=FieldStatus.CONFIRMED,
                    ai_normalized=True,
                    requires_human_confirmation=True,
                )
            )
        return additions
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run pytest tests/unit/test_extractor.py -v`
Expected: PASS, all extractor tests including the 5 new ones.

- [ ] **Step 6: Wire the descriptions in at bootstrap**

In `src/ed_gateway/bootstrap.py`, replace line 40 inside `create_orchestrator`:

```python
        extractor=ResponseExtractor(
            create_llm_client(settings),
            {rule.observation_field: rule.detection_concepts_en for rule in config.safety_rules},
        ),
```

- [ ] **Step 7: Run the full suite and quality gates**

Run: `UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run pytest && UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run ruff check . && UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run mypy`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/ed_gateway/application/extractor.py src/ed_gateway/bootstrap.py tests/unit/test_extractor.py
git commit -m "feat: merge validated multilingual safety proposals as add-only detections"
```

---

### Task 3: Ask the provider for it

Without this task the extractor validates a key the model was never asked to produce.

**Files:**
- Modify: `src/ed_gateway/llm/openai_compatible.py:29-38`
- Test: `tests/unit/test_openai_compatible_prompt.py` (create)

**Interfaces:**
- Consumes: `context["safety_categories"]` from Task 2.
- Produces: `OpenAICompatibleClient._build_prompt(text, expected_field, context) -> str`.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_openai_compatible_prompt.py`:

```python
from ed_gateway.llm.openai_compatible import OpenAICompatibleClient


def _client() -> OpenAICompatibleClient:
    return OpenAICompatibleClient(
        base_url="https://llm.example/v1",
        api_key="unused",
        model="test-model",
        timeout=1,
        max_retries=0,
        temperature=0,
    )


def test_prompt_is_language_neutral_and_lists_the_categories() -> None:
    prompt = _client()._build_prompt(
        text="my arm went weak",
        expected_field="symptom.onset",
        context={"safety_categories": {"safety.neurological": ["weakness on one side"]}},
    )
    assert "Traditional Chinese" not in prompt
    assert "any language" in prompt
    assert "other_safety_categories" in prompt
    assert "safety.neurological: weakness on one side" in prompt


def test_prompt_omits_the_category_section_when_none_are_supplied() -> None:
    prompt = _client()._build_prompt(
        text="三十四歲",
        expected_field="demographics.age",
        context={"respondent_type": "PATIENT"},
    )
    assert "other_safety_categories" in prompt
    assert "safety." not in prompt


def test_prompt_does_not_repeat_the_category_list_in_the_context_dump() -> None:
    prompt = _client()._build_prompt(
        text="my arm went weak",
        expected_field="symptom.onset",
        context={
            "respondent_type": "PATIENT",
            "safety_categories": {"safety.neurological": ["weakness on one side"]},
        },
    )
    assert prompt.count("weakness on one side") == 1
    assert "PATIENT" in prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run pytest tests/unit/test_openai_compatible_prompt.py -v`
Expected: FAIL with `AttributeError: 'OpenAICompatibleClient' object has no attribute '_build_prompt'`

- [ ] **Step 3: Extract and rewrite the prompt**

In `src/ed_gateway/llm/openai_compatible.py`, replace the inline `prompt = (...)` assignment at the top of `extract()` with a call, and add the two methods. Keep the rest of `extract()` (payload, headers, retry loop) exactly as it is.

```python
    async def extract(self, *, text: str, expected_field: str, context: dict[str, Any]) -> dict[str, Any]:
        prompt = self._build_prompt(text=text, expected_field=expected_field, context=context)
        payload = {
```

```python
    def _build_prompt(self, *, text: str, expected_field: str, context: dict[str, Any]) -> str:
        other_context = {key: value for key, value in context.items() if key != "safety_categories"}
        return (
            "Classify the supplied emergency-intake answer into JSON only. The answer may be in "
            "any language; interpret it by meaning rather than by matching words. "
            "Do not diagnose, triage, recommend treatment, or infer missing measurements. "
            "Distinguish current symptom, denial, past history, family history, hypothetical "
            "question, caregiver statement, measurement, and ambiguity. Return keys "
            "classification, normalized_value, status, requires_human_confirmation, "
            "other_safety_categories.\n"
            f"{self._safety_category_section(context)}"
            f"Expected field: {expected_field}\n"
            f"Context: {json.dumps(other_context, ensure_ascii=False)}\n"
            f"Answer: {text}"
        )

    @staticmethod
    def _safety_category_section(context: dict[str, Any]) -> str:
        categories = context.get("safety_categories")
        if not isinstance(categories, dict) or not categories:
            return ""
        listed = "\n".join(
            f"- {field}: {'; '.join(concepts)}" for field, concepts in sorted(categories.items())
        )
        return (
            "In other_safety_categories, list the field keys below whose condition this answer "
            "reports as present for this patient right now, and use [] when none apply. Never "
            "list one for a denial, a past episode, a family member's history, or a hypothetical "
            "question.\n"
            f"{listed}\n"
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run pytest tests/unit/test_openai_compatible_prompt.py -v`
Expected: PASS, 3 passed.

- [ ] **Step 5: Run the full suite and quality gates**

Run: `UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run pytest && UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run ruff check . && UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run mypy`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/ed_gateway/llm/openai_compatible.py tests/unit/test_openai_compatible_prompt.py
git commit -m "feat: ask the provider to screen all warning categories in any language"
```

---

### Task 4: Degrade instead of crashing when the provider fails

Also closes a pre-existing defect: `orchestrator.py:79` has no exception handling, so any provider timeout or connection failure currently returns a 500 mid-interview.

**Files:**
- Modify: `src/ed_gateway/domain/models.py:82-100`
- Modify: `src/ed_gateway/application/extractor.py`
- Modify: `src/ed_gateway/application/orchestrator.py:78-79`
- Test: `tests/unit/test_extractor.py`
- Test: `tests/unit/test_orchestrator.py` (create)

**Interfaces:**
- Consumes: `ResponseExtractor` from Task 2.
- Produces: `SafetyScanDegraded(partial_observations: list[Observation])` exported from `ed_gateway.application.extractor`; `InterviewState.safety_scan_degraded: list[str]`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_extractor.py`:

```python
async def test_provider_failure_raises_with_local_observations(state) -> None:
    class FailingLLM:
        async def extract(self, **_kwargs):
            raise httpx.ConnectError("provider unreachable")

    with pytest.raises(SafetyScanDegraded) as caught:
        await ResponseExtractor(FailingLLM(), SAFETY_CATEGORIES).extract(
            text="我現在突然半邊無力",
            expected_field="symptom.onset",
            state=state,
        )

    fields = {item.field_key for item in caught.value.partial_observations}
    assert "safety.neurological" in fields
```

Add `import httpx` and extend the extractor import to `from ed_gateway.application.extractor import ResponseExtractor, SafetyScanDegraded` at the top of that file.

Create `tests/unit/test_orchestrator.py`:

```python
import httpx

from ed_gateway.application.repository import InMemoryInterviewRepository
from ed_gateway.bootstrap import create_orchestrator
from ed_gateway.domain.models import CreateSessionRequest
from ed_gateway.settings import Settings


class _FailingLLM:
    async def extract(self, **_kwargs):
        raise httpx.ReadTimeout("provider timed out")


async def test_provider_failure_completes_the_turn_and_records_it(monkeypatch) -> None:
    monkeypatch.setattr("ed_gateway.bootstrap.create_llm_client", lambda settings: _FailingLLM())
    repository = InMemoryInterviewRepository()
    orchestrator = create_orchestrator(
        repository=repository,
        settings=Settings(APP_ENV="test", LLM_PROVIDER="mock", _env_file=None),
    )
    started = await orchestrator.create_session(CreateSessionRequest())

    turn = await orchestrator.handle_message(started.session_id, "我是病人本人")

    assert turn.patient_message
    state = await orchestrator.get_state(started.session_id)
    assert state.safety_scan_degraded == ["我是病人本人"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run pytest tests/unit/test_orchestrator.py tests/unit/test_extractor.py -v -k "degraded or provider_failure"`
Expected: FAIL with `ImportError: cannot import name 'SafetyScanDegraded'`

- [ ] **Step 3: Add the state field**

In `src/ed_gateway/domain/models.py`, add one field to `InterviewState`, directly after `contradictions`:

```python
    contradictions: list[str] = Field(default_factory=list)
    safety_scan_degraded: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Raise on provider failure, carrying what was computed locally**

In `src/ed_gateway/application/extractor.py`, add the exception near the top, after the module constants:

```python
class SafetyScanDegraded(Exception):
    """The provider call failed, so this turn was screened by the keyword layer only."""

    def __init__(self, partial_observations: list[Observation]) -> None:
        super().__init__("multilingual safety screen unavailable for this turn")
        self.partial_observations = partial_observations
```

Then wrap only the provider call in `extract()`:

```python
        try:
            proposal = await self._llm.extract(
                text=text,
                expected_field=expected_field,
                context={
                    "respondent_type": state.respondent_type.value,
                    "classification": classification,
                    "safety_categories": self._safety_categories,
                },
            )
        except Exception as error:
            raise SafetyScanDegraded(observations) from error
```

- [ ] **Step 5: Handle it in the orchestrator**

In `src/ed_gateway/application/orchestrator.py`, add `SafetyScanDegraded` to the existing extractor import, then replace line 79:

```python
        try:
            observations = await self._extractor.extract(
                text=content, expected_field=question.target_field, state=state
            )
        except SafetyScanDegraded as degraded:
            observations = degraded.partial_observations
            state.safety_scan_degraded.append(content)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run pytest tests/unit/test_orchestrator.py tests/unit/test_extractor.py -v`
Expected: PASS.

- [ ] **Step 7: Run the full suite and quality gates**

Run: `UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run pytest && UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run ruff check . && UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run mypy`
Expected: all pass. If Ruff flags the broad `except Exception`, keep the broad catch — any provider error must degrade rather than crash — and narrow the lint with a targeted `# noqa` plus the reason.

- [ ] **Step 8: Commit**

```bash
git add src/ed_gateway/domain/models.py src/ed_gateway/application/extractor.py src/ed_gateway/application/orchestrator.py tests/unit/test_extractor.py tests/unit/test_orchestrator.py
git commit -m "fix: degrade to keyword-only screening when the provider call fails"
```

---

### Task 5: Tell the nurse which answers were not screened

**Files:**
- Modify: `src/ed_gateway/application/drafts.py:168-172`
- Test: `tests/unit/test_drafts.py`

**Interfaces:**
- Consumes: `InterviewState.safety_scan_degraded` from Task 4.
- Produces: nothing for later tasks.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_drafts.py`:

```python
def test_degraded_scan_is_flagged_for_manual_nurse_review(clinical_config, state) -> None:
    state.safety_scan_degraded = ["my chest feels tight"]
    draft = DraftGenerator(
        clinical_config,
        Path(__file__).parents[2] / "config" / "nurse-draft-template.md",
    ).generate(state)
    assert "未能執行" in draft.rendered_markdown
    assert "my chest feels tight" in draft.rendered_markdown


def test_review_points_are_unchanged_when_the_scan_ran(clinical_config, state) -> None:
    draft = DraftGenerator(
        clinical_config,
        Path(__file__).parents[2] / "config" / "nurse-draft-template.md",
    ).generate(state)
    assert "未能執行" not in draft.rendered_markdown
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run pytest tests/unit/test_drafts.py -v -k "degraded or unchanged_when"`
Expected: FAIL — `assert "未能執行" in draft.rendered_markdown` fails.

- [ ] **Step 3: Append the note in `_review_points`**

In `src/ed_gateway/application/drafts.py`, replace `_review_points`:

```python
    @staticmethod
    def _review_points(state: InterviewState) -> str:
        if state.triggered_rule_ids:
            points = ["立即確認警訊、觸發原話、發生時間與尚未取得的關鍵資料。"]
        else:
            points = ["確認原話、正規化內容、資料來源、缺失欄位與矛盾資料。"]
        if state.safety_scan_degraded:
            quoted = "、".join(f"「{answer}」" for answer in state.safety_scan_degraded)
            points.append(
                f"以下 {len(state.safety_scan_degraded)} 則回答的跨語言警訊掃描未能執行，"
                f"請人工複查原文是否含警訊：{quoted}"
            )
        return "\n".join(points)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run pytest tests/unit/test_drafts.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite and quality gates**

Run: `UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run pytest && UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run ruff check . && UV_CACHE_DIR=/tmp/ed-gateway-uv-cache uv run mypy`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/ed_gateway/application/drafts.py tests/unit/test_drafts.py
git commit -m "feat: flag unscreened answers in the nurse review points"
```

---

### Task 6: Live verification against the real provider

Green unit tests do not show that a real model returns the new key. Nothing is complete until a real provider screens a real non-Chinese warning sign.

**Files:**
- Modify: `STATE.md`

**Interfaces:**
- Consumes: Tasks 1-5.
- Produces: recorded evidence.

- [ ] **Step 1: Rebuild and confirm the stack is healthy**

```bash
docker compose up -d --build
docker compose ps
curl -fsS http://127.0.0.1:8001/health/ready
```
Expected: `db`, `api`, `web` healthy; readiness reports `"llm":"openai_compatible"`. If it reports `mock`, the live path is not being exercised — stop and fix `.env` before continuing.

- [ ] **Step 2: Screen a non-Chinese warning sign stated while a different field is being asked**

```bash
curl -fsS -X POST http://127.0.0.1:8001/api/v1/interview-sessions \
  -H "Content-Type: application/json" -d '{}' -o /tmp/s.json -w "%{http_code}\n"
SID=$(python3 -c "import json;print(json.load(open('/tmp/s.json'))['session_id'])")
curl -sS -X POST "http://127.0.0.1:8001/api/v1/interview-sessions/$SID/messages" \
  -H "Content-Type: application/json" -d '{"content":"我是病人本人"}' -o /tmp/t1.json -w "%{http_code}\n"
curl -sS -X POST "http://127.0.0.1:8001/api/v1/interview-sessions/$SID/messages" \
  -H "Content-Type: application/json" \
  -d '{"content":"I am 40, and my left arm suddenly went weak"}' -o /tmp/t2.json -w "%{http_code}\n"
python3 -c "import json;print(json.dumps(json.load(open('/tmp/t2.json')),ensure_ascii=False,indent=2))"
```
Expected: `200` for each turn, and the final response escalates — `safety_status` is `TRIGGERED` with `WARN-NEUROLOGICAL` in `triggered_rule_ids`. Do not use `echo "$VAR"` on JSON in zsh; it converts `\n` to real newlines and corrupts the payload.

- [ ] **Step 3: Confirm the Chinese path still behaves as before**

Repeat Step 2 with `{"content":"我現在突然半邊無力"}` as the second answer.
Expected: still escalates with `WARN-NEUROLOGICAL`, unchanged from before this feature.

- [ ] **Step 4: Confirm a mundane answer is not falsely escalated**

Repeat Step 2 with `{"content":"I am 34 years old"}` as the second answer.
Expected: `200`, `safety_status` not `TRIGGERED`, and the interview advances to the next question.

- [ ] **Step 5: Check the logs for the degraded path**

```bash
docker compose logs --no-log-prefix api --tail=40
```
Expected: no tracebacks, no raw interview text in the log output.

- [ ] **Step 6: Record the evidence in `STATE.md`**

Update `STATE.md` with: the commit range, what each live scenario returned, whether the degraded path was exercised live or only in tests, and the residual scope carried over verbatim from the spec's "Residual scope" section. State plainly that no per-language evaluation was run.

- [ ] **Step 7: Commit**

```bash
git add STATE.md
git commit -m "docs: record live verification of multilingual safety detection"
```

---

## Self-Review

**Spec coverage:** All seven spec component changes map to tasks — config (T1), `SafetyRuleDefinition` (T1), `bootstrap.py` (T2), `ResponseExtractor` (T2, T4), `OpenAICompatibleClient` (T3), failure handling (T4), `_review_points` (T5). The spec's testing plan maps to T1-T5 plus the live verification in T6. The spec's requirement that implementation record the unreviewed English wording in `docs/open-clinical-decisions.md` is T1 Step 5.

**Type consistency:** `safety_categories: dict[str, list[str]]` is the constructor parameter in T2 and the `context` key in T2/T3; `other_safety_categories: list[str]` is the proposal key in T2/T3; `_build_prompt` is defined and called in T3 only; `SafetyScanDegraded.partial_observations` is defined in T4 and consumed in T4; `safety_scan_degraded: list[str]` is defined in T4 and consumed in T4/T5; `{"present": True, "detected_by": "llm_semantic_screen"}` is identical in T2's implementation and T2's assertion.

**Known deliberate choices:**
- `safety_categories` defaults to `{}` so the 20 existing `ResponseExtractor(llm)` call sites in `tests/unit/test_extractor.py` keep working. Without the default this becomes a 20-file-site edit for no behavioural gain.
- T4 catches broad `Exception` around the provider call on purpose: any provider error must degrade rather than crash. Narrowing it would let an unanticipated error type reach the respondent as a 500.
- The keyword sweep and `SafetyGate` are not touched by any task. If a task requires changing either, stop and re-open the design.
