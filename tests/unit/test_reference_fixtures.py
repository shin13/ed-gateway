from pathlib import Path

import pytest
import yaml

from ed_gateway.application.extractor import ResponseExtractor
from ed_gateway.application.planner import QuestionPlanner
from ed_gateway.application.safety import SafetyGate
from ed_gateway.domain.models import FieldStatus, InformationSource, Observation, SafetyStatus
from ed_gateway.llm.mock import MockLLMClient


def _cases() -> list[dict[str, str]]:
    path = Path(__file__).parents[1] / "fixtures" / "reference_complaints.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data["cases"]


@pytest.mark.parametrize("case", _cases(), ids=lambda case: case["id"])
async def test_reference_fixture_uses_common_engine(case, state, clinical_config) -> None:
    by_id = {question.id: question for question in clinical_config.questions}
    required_ids = [
        "respondent_type",
        "age",
        "safety_cardiovascular",
        "safety_neurological",
        "safety_respiratory",
        "safety_circulation",
        "safety_bleeding",
        "safety_allergy",
        "safety_infection_temperature",
        "safety_severe_pain",
        "safety_trauma",
        "safety_hypertensive",
        "safety_mental_health",
        "safety_self_identified_danger",
        "symptom_onset",
        "symptom_location",
        "symptom_quality",
        "symptom_severity",
        "symptom_course",
        "symptom_associated",
        "symptom_trauma",
        "symptom_function",
    ]
    expected_rule = case.get("expected_safety_rule")
    expected_rule_field = next(
        (rule.observation_field for rule in clinical_config.safety_rules if rule.id == expected_rule),
        None,
    )
    for question_id in required_ids:
        question = by_id[question_id]
        if question.target_field == expected_rule_field:
            continue
        is_safety = question.target_field.startswith("safety.")
        value = {"present": False} if is_safety else "synthetic answer"
        if question_id == "respondent_type":
            value = "PATIENT"
        elif question_id == "age":
            value = 35
        state.merge_observation(
            Observation(
                field_key=question.target_field,
                verbatim_text=str(value),
                normalized_value=value,
                source=InformationSource.PATIENT_STATEMENT,
                status=FieldStatus.DENIED if is_safety else FieldStatus.CONFIRMED,
            )
        )

    observations = await ResponseExtractor(MockLLMClient()).extract(
        text=case["complaint"], expected_field="symptom.chief_complaint", state=state
    )
    for observation in observations:
        state.merge_observation(observation)
    complaint = next(item for item in observations if item.field_key == "symptom.chief_complaint")
    assert complaint.status == FieldStatus.CONFIRMED
    assert complaint.verbatim_text == case["complaint"]
    assert complaint.normalized_value["label"] == case["normalized_label"]
    if expected_rule:
        decision = SafetyGate(clinical_config.safety_rules).evaluate(state)
        assert decision.status == SafetyStatus.TRIGGERED
        assert expected_rule in decision.triggered_rule_ids
    else:
        assert QuestionPlanner(clinical_config).next_question(state).id == case["expected_context_question"]
