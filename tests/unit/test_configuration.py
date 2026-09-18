from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from ed_gateway.application.configuration import load_clinical_config
from ed_gateway.settings import Settings


def test_clinical_configuration_loads_and_has_twelve_safety_rules() -> None:
    config = load_clinical_config(Path(__file__).parents[2] / "config")

    assert config.safety_version == "clinical-review-draft-v1"
    assert len(config.safety_rules) == 12
    assert len({rule.id for rule in config.safety_rules}) == 12


def test_every_safety_rule_has_english_detection_concepts() -> None:
    config = load_clinical_config(Path(__file__).parents[2] / "config")

    for rule in config.safety_rules:
        assert rule.detection_concepts_en, f"{rule.id} has no English detection concepts"


def test_configuration_rejects_context_reference_to_unknown_question(tmp_path: Path) -> None:
    source = Path(__file__).parents[2] / "config"
    for name in ("interview-schema.yaml", "question-catalog.yaml", "safety-rules.yaml"):
        (tmp_path / name).write_text((source / name).read_text(), encoding="utf-8")
    invalid = {
        "version": "1",
        "rules": [{"id": "bad", "complaint_labels": ["x"], "priority_question_ids": ["missing"]}],
    }
    (tmp_path / "context-rules.yaml").write_text(yaml.safe_dump(invalid), encoding="utf-8")

    with pytest.raises(ValidationError, match="unknown questions"):
        load_clinical_config(tmp_path)


def test_mock_settings_require_no_api_key() -> None:
    settings = Settings(LLM_PROVIDER="mock", LLM_API_KEY="", _env_file=None)
    assert settings.LLM_PROVIDER == "mock"
    assert "LLM_API_KEY" not in repr(settings)


def test_live_provider_requires_all_settings() -> None:
    with pytest.raises(ValidationError, match="LLM_MODEL"):
        Settings(LLM_PROVIDER="openai_compatible", _env_file=None)


def test_live_provider_accepts_complete_configuration() -> None:
    settings = Settings(
        LLM_PROVIDER="openai_compatible",
        LLM_MODEL="test-model",
        LLM_BASE_URL="https://llm.example/v1",
        LLM_API_KEY="secret",
        _env_file=None,
    )
    assert settings.LLM_MODEL == "test-model"
    assert "secret" not in repr(settings)
