from ed_gateway.application.planner import QuestionPlanner
from ed_gateway.domain.models import FieldStatus, InformationSource, Observation


def _answer(state, field: str, value="ok", status: FieldStatus = FieldStatus.CONFIRMED) -> None:
    state.merge_observation(
        Observation(
            field_key=field,
            verbatim_text=str(value),
            normalized_value=value,
            source=InformationSource.PATIENT_STATEMENT,
            status=status,
        )
    )


def test_question_priority_starts_with_respondent(clinical_config, state) -> None:
    planner = QuestionPlanner(clinical_config)
    assert planner.next_question(state).id == "respondent_type"


def test_age_follows_respondent(clinical_config, state) -> None:
    planner = QuestionPlanner(clinical_config)
    _answer(state, "respondent.type", "PATIENT")
    assert planner.next_question(state).id == "age"


def test_safety_sequence_precedes_chief_complaint(clinical_config, state) -> None:
    planner = QuestionPlanner(clinical_config)
    _answer(state, "respondent.type", "PATIENT")
    _answer(state, "demographics.age", 35)
    assert planner.next_question(state).id == "safety_cardiovascular"


def test_skip_counts_as_answer_and_prevents_repeat(clinical_config, state) -> None:
    planner = QuestionPlanner(clinical_config)
    _answer(state, "respondent.type", None, FieldStatus.DECLINED)
    assert planner.next_question(state).id == "age"


def test_non_safety_ambiguity_is_reasked_once(clinical_config, state) -> None:
    planner = QuestionPlanner(clinical_config)
    _answer(state, "symptom.onset", None, FieldStatus.NEEDS_CLARIFICATION)
    assert planner.next_question(state).id == "symptom_onset"
    state.clarification_counts["symptom.onset"] = 1
    assert planner.next_question(state).id == "respondent_type"


def test_dizziness_context_question_uses_shared_catalog(clinical_config, state) -> None:
    planner = QuestionPlanner(clinical_config)
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
        "chief_complaint",
        "symptom_onset",
        "symptom_location",
        "symptom_quality",
        "symptom_severity",
        "symptom_course",
        "symptom_associated",
        "symptom_trauma",
        "symptom_function",
    ]
    by_id = {question.id: question for question in clinical_config.questions}
    for question_id in required_ids:
        question = by_id[question_id]
        if question_id == "respondent_type":
            value = "PATIENT"
        elif question_id == "chief_complaint":
            value = {"label": "dizziness"}
        else:
            value = "ok"
        _answer(state, question.target_field, value)
    assert planner.next_question(state).id == "dizziness_character"
