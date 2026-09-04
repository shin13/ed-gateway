from __future__ import annotations

from uuid import UUID, uuid4

from ed_gateway.application.repository import InterviewRepository
from ed_gateway.domain.models import (
    FieldStatus,
    InformationSource,
    InteractionMode,
    InterviewPhase,
    InterviewState,
    Observation,
    SafetyStatus,
    utc_now,
)


class InterviewSessionManager:
    def __init__(self, repository: InterviewRepository, rule_version: str) -> None:
        self._repository = repository
        self._rule_version = rule_version

    async def create(self, *, interaction_mode: InteractionMode, answer_language: str) -> InterviewState:
        state = InterviewState(
            session_id=uuid4(),
            phase=InterviewPhase.RESPONDENT,
            interaction_mode=interaction_mode,
            answer_language=answer_language,
            rule_version=self._rule_version,
        )
        for field_key, value in (
            ("interaction.mode", interaction_mode.value),
            ("interaction.answer_language", answer_language),
        ):
            state.merge_observation(
                Observation(
                    field_key=field_key,
                    verbatim_text="session configuration",
                    normalized_value=value,
                    source=InformationSource.AI_NORMALIZATION,
                    status=FieldStatus.CONFIRMED,
                    ai_normalized=True,
                )
            )
        return state

    async def retrieve(self, session_id: UUID) -> InterviewState | None:
        return await self._repository.get_state(session_id)

    @staticmethod
    def update(state: InterviewState, observation: Observation) -> None:
        state.merge_observation(observation)

    @staticmethod
    def finish(state: InterviewState) -> None:
        state.phase = InterviewPhase.DRAFT_READY
        state.updated_at = utc_now()

    @staticmethod
    def stop(state: InterviewState) -> None:
        state.phase = InterviewPhase.STOPPED
        state.updated_at = utc_now()

    @staticmethod
    def escalate(state: InterviewState, triggered_rule_ids: list[str]) -> None:
        state.phase = InterviewPhase.ESCALATED
        state.safety_status = SafetyStatus.TRIGGERED
        state.triggered_rule_ids = triggered_rule_ids
        state.updated_at = utc_now()
