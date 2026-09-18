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
