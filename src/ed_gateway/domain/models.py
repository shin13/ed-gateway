from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class InterviewPhase(StrEnum):
    STARTER = "STARTER"
    RESPONDENT = "RESPONDENT"
    AGE = "AGE"
    SAFETY_SCREEN = "SAFETY_SCREEN"
    SYMPTOM_COLLECTION = "SYMPTOM_COLLECTION"
    REVIEW = "REVIEW"
    DRAFT_READY = "DRAFT_READY"
    ESCALATED = "ESCALATED"
    STOPPED = "STOPPED"


class InformationSource(StrEnum):
    PATIENT_STATEMENT = "PATIENT_STATEMENT"
    CAREGIVER_STATEMENT = "CAREGIVER_STATEMENT"
    DEVICE_MEASUREMENT = "DEVICE_MEASUREMENT"
    CLINICIAN_MEASUREMENT = "CLINICIAN_MEASUREMENT"
    AI_NORMALIZATION = "AI_NORMALIZATION"


class FieldStatus(StrEnum):
    NOT_OBTAINED = "NOT_OBTAINED"
    CONFIRMED = "CONFIRMED"
    DENIED = "DENIED"
    UNKNOWN = "UNKNOWN"
    DECLINED = "DECLINED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


class RespondentType(StrEnum):
    PATIENT = "PATIENT"
    CAREGIVER = "CAREGIVER"
    UNKNOWN = "UNKNOWN"


class InteractionMode(StrEnum):
    TEXT = "TEXT"
    VOICE = "VOICE"


class SafetyStatus(StrEnum):
    CLEAR = "CLEAR"
    PENDING = "PENDING"
    TRIGGERED = "TRIGGERED"


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_key: str
    verbatim_text: str
    normalized_value: Any = None
    source: InformationSource
    status: FieldStatus
    observed_at: datetime = Field(default_factory=utc_now)
    ai_normalized: bool = False
    requires_human_confirmation: bool = False

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        return value.astimezone(UTC)


class InterviewState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    phase: InterviewPhase = InterviewPhase.STARTER
    respondent_type: RespondentType = RespondentType.UNKNOWN
    interaction_mode: InteractionMode = InteractionMode.TEXT
    answer_language: str = "繁體中文"
    observations: dict[str, Observation] = Field(default_factory=dict)
    observation_history: list[Observation] = Field(default_factory=list)
    asked_question_ids: list[str] = Field(default_factory=list)
    clarification_counts: dict[str, int] = Field(default_factory=dict)
    triggered_rule_ids: list[str] = Field(default_factory=list)
    safety_status: SafetyStatus = SafetyStatus.PENDING
    rule_version: str = "clinical-review-draft-v1"
    missing_fields: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def merge_observation(self, observation: Observation) -> None:
        previous = self.observations.get(observation.field_key)
        contradictory_pair = {FieldStatus.CONFIRMED, FieldStatus.DENIED}
        if previous and {previous.status, observation.status} == contradictory_pair:
            self.contradictions.append(
                f"{observation.field_key}: {previous.status.value} -> {observation.status.value}"
            )
            observation = observation.model_copy(
                update={
                    "status": FieldStatus.NEEDS_CLARIFICATION,
                    "requires_human_confirmation": True,
                }
            )
        self.observations[observation.field_key] = observation
        self.observation_history.append(observation)
        self.updated_at = utc_now()

        if observation.field_key == "respondent.type" and observation.status == FieldStatus.CONFIRMED:
            self.respondent_type = RespondentType(observation.normalized_value)


class SafetyDecision(BaseModel):
    status: SafetyStatus
    triggered_rule_ids: list[str] = Field(default_factory=list)
    requires_clarification: bool = False
    clarification_field: str | None = None


class DraftPayload(BaseModel):
    revision: int
    structured: dict[str, Any]
    rendered_markdown: str
    created_at: datetime = Field(default_factory=utc_now)


class TurnResponse(BaseModel):
    session_id: UUID
    phase: InterviewPhase
    patient_message: str
    next_question_id: str | None = None
    safety_status: SafetyStatus
    triggered_rule_ids: list[str] = Field(default_factory=list)
    completed: bool = False
    draft: DraftPayload | None = None


class SessionView(BaseModel):
    session_id: UUID
    phase: InterviewPhase
    respondent_type: RespondentType
    interaction_mode: InteractionMode
    state: InterviewState
    created_at: datetime
    updated_at: datetime


class CreateSessionRequest(BaseModel):
    interaction_mode: InteractionMode = InteractionMode.TEXT
    answer_language: str = "繁體中文"


class MessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("content must not be blank")
        return value
