from __future__ import annotations

from ed_gateway.application.configuration import ClinicalConfig, QuestionDefinition
from ed_gateway.domain.models import FieldStatus, InterviewPhase, InterviewState


class QuestionPlanner:
    def __init__(self, config: ClinicalConfig) -> None:
        self._config = config
        self._by_id = {question.id: question for question in config.questions}

    def question_for_field(self, field: str) -> QuestionDefinition | None:
        return next((q for q in self._config.questions if q.target_field == field), None)

    def question_by_id(self, question_id: str) -> QuestionDefinition:
        return self._by_id[question_id]

    def next_question(self, state: InterviewState) -> QuestionDefinition | None:
        for field, observation in state.observations.items():
            if observation.status == FieldStatus.NEEDS_CLARIFICATION and state.clarification_counts.get(field, 0) < 1:
                question = self.question_for_field(field)
                if question is not None:
                    return question

        ordered = [
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
        for question_id in ordered:
            question = self._by_id[question_id]
            if question.target_field not in state.observations:
                return question

        complaint = state.observations.get("symptom.chief_complaint")
        label = (
            complaint.normalized_value.get("label")
            if complaint and isinstance(complaint.normalized_value, dict)
            else None
        )
        for rule in self._config.context_rules:
            if label not in rule.complaint_labels:
                continue
            for question_id in rule.priority_question_ids:
                question = self._by_id[question_id]
                if question.target_field not in state.observations:
                    return question

        optional = [
            "arrival_source",
            "medical_history",
            "medications",
            "allergies",
            "tocc_exposure",
            "vitals",
        ]
        for question_id in optional:
            question = self._by_id[question_id]
            if question.target_field not in state.observations:
                return question
        return None

    @staticmethod
    def phase_for(question: QuestionDefinition | None) -> InterviewPhase:
        if question is None:
            return InterviewPhase.REVIEW
        return question.phase
