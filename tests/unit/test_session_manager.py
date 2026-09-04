from ed_gateway.application.repository import InMemoryInterviewRepository
from ed_gateway.application.session_manager import InterviewSessionManager
from ed_gateway.domain.models import (
    FieldStatus,
    InformationSource,
    InteractionMode,
    InterviewPhase,
    Observation,
    SafetyStatus,
)


async def test_session_manager_owns_lifecycle_transitions() -> None:
    manager = InterviewSessionManager(InMemoryInterviewRepository(), "clinical-review-draft-v1")
    state = await manager.create(interaction_mode=InteractionMode.TEXT, answer_language="繁體中文")

    assert state.observations["interaction.mode"].normalized_value == "TEXT"
    assert state.observations["interaction.answer_language"].normalized_value == "繁體中文"
    assert state.observations["interaction.mode"].ai_normalized is True

    manager.update(
        state,
        Observation(
            field_key="demographics.age",
            verbatim_text="34歲",
            normalized_value=34,
            source=InformationSource.PATIENT_STATEMENT,
            status=FieldStatus.CONFIRMED,
        ),
    )
    assert state.observations["demographics.age"].normalized_value == 34

    manager.finish(state)
    assert state.phase == InterviewPhase.DRAFT_READY
    manager.stop(state)
    assert state.phase == InterviewPhase.STOPPED
    manager.escalate(state, ["WARN-TEST"])
    assert state.phase == InterviewPhase.ESCALATED
    assert state.safety_status == SafetyStatus.TRIGGERED
    assert state.triggered_rule_ids == ["WARN-TEST"]
