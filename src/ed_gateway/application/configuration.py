from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ed_gateway.domain.models import InterviewPhase


class QuestionDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    target_field: str
    wording: str
    answer_type: str
    required: bool
    phase: InterviewPhase
    applicability: dict[str, Any] = Field(default_factory=dict)
    safety_relevance: str | None = None
    clarification_wording: str | None = None


class SafetyRuleDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    category: str
    observation_field: str
    trigger_statuses: list[str] = Field(default_factory=lambda: ["CONFIRMED"])
    clinical_review_status: str
    detection_concepts_en: list[str] = Field(default_factory=list)


class ContextRuleDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    complaint_labels: list[str]
    priority_question_ids: list[str]


class InterviewSchemaConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    observation_fields: list[str]
    required_draft_sections: list[str]


class ClinicalConfig(BaseModel):
    interview_schema: InterviewSchemaConfig
    questions: list[QuestionDefinition]
    safety_version: str
    safety_rules: list[SafetyRuleDefinition]
    context_rules: list[ContextRuleDefinition]

    @model_validator(mode="after")
    def validate_references(self) -> ClinicalConfig:
        question_ids = {question.id for question in self.questions}
        if len(question_ids) != len(self.questions):
            raise ValueError("question IDs must be unique")
        if len({rule.id for rule in self.safety_rules}) != len(self.safety_rules):
            raise ValueError("safety rule IDs must be unique")
        schema_fields = set(self.interview_schema.observation_fields)
        missing_safety_fields = {rule.observation_field for rule in self.safety_rules} - schema_fields
        if missing_safety_fields:
            raise ValueError(f"safety rules reference fields outside the interview schema: {missing_safety_fields}")
        for rule in self.context_rules:
            missing = set(rule.priority_question_ids) - question_ids
            if missing:
                raise ValueError(f"context rule {rule.id} references unknown questions: {missing}")
        return self


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return value


def load_clinical_config(root: Path | None = None) -> ClinicalConfig:
    config_root = root or Path(__file__).resolve().parents[3] / "config"
    schema = InterviewSchemaConfig.model_validate(_load_yaml(config_root / "interview-schema.yaml"))
    questions_data = _load_yaml(config_root / "question-catalog.yaml")
    safety_data = _load_yaml(config_root / "safety-rules.yaml")
    context_data = _load_yaml(config_root / "context-rules.yaml")
    return ClinicalConfig(
        interview_schema=schema,
        questions=[QuestionDefinition.model_validate(item) for item in questions_data["questions"]],
        safety_version=safety_data["version"],
        safety_rules=[SafetyRuleDefinition.model_validate(item) for item in safety_data["rules"]],
        context_rules=[ContextRuleDefinition.model_validate(item) for item in context_data["rules"]],
    )
