from datetime import datetime

import pytest
from pydantic import ValidationError

from ed_gateway.domain.models import FieldStatus, InformationSource, Observation


def test_observation_requires_timezone() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        Observation(
            field_key="symptom.location",
            verbatim_text="左邊",
            normalized_value="left",
            source=InformationSource.PATIENT_STATEMENT,
            status=FieldStatus.CONFIRMED,
            observed_at=datetime(2026, 9, 4),
        )


def test_observation_keeps_verbatim_separate_from_normalized() -> None:
    observation = Observation(
        field_key="symptom.chief_complaint",
        verbatim_text="我個腰痠痠痛痛",
        normalized_value={"label": "lower_back_pain"},
        source=InformationSource.CAREGIVER_STATEMENT,
        status=FieldStatus.CONFIRMED,
        ai_normalized=True,
    )
    assert observation.verbatim_text == "我個腰痠痠痛痛"
    assert observation.normalized_value == {"label": "lower_back_pain"}
    assert observation.source == InformationSource.CAREGIVER_STATEMENT


def test_clarification_resolution_is_not_recorded_as_contradiction(state) -> None:
    for status in (FieldStatus.NEEDS_CLARIFICATION, FieldStatus.DENIED):
        state.merge_observation(
            Observation(
                field_key="safety.cardiovascular",
                verbatim_text=status.value,
                normalized_value={"present": False} if status == FieldStatus.DENIED else None,
                source=InformationSource.PATIENT_STATEMENT,
                status=status,
            )
        )
    assert state.contradictions == []


def test_confirmed_then_denied_is_recorded_as_contradiction(state) -> None:
    for status in (FieldStatus.CONFIRMED, FieldStatus.DENIED):
        state.merge_observation(
            Observation(
                field_key="safety.cardiovascular",
                verbatim_text=status.value,
                normalized_value={"present": status == FieldStatus.CONFIRMED},
                source=InformationSource.PATIENT_STATEMENT,
                status=status,
            )
        )
    assert state.contradictions == ["safety.cardiovascular: CONFIRMED -> DENIED"]
    assert state.observations["safety.cardiovascular"].status == FieldStatus.NEEDS_CLARIFICATION
    assert state.observations["safety.cardiovascular"].requires_human_confirmation is True
