from ed_gateway.application.safety import SafetyGate
from ed_gateway.domain.models import FieldStatus, InformationSource, Observation, SafetyStatus


def _observation(field: str, status: FieldStatus, present: bool | None = None) -> Observation:
    return Observation(
        field_key=field,
        verbatim_text="測試原話",
        normalized_value={"present": present} if present is not None else None,
        source=InformationSource.PATIENT_STATEMENT,
        status=status,
    )


def test_confirmed_warning_triggers(clinical_config, state) -> None:
    state.merge_observation(_observation("safety.neurological", FieldStatus.CONFIRMED, True))
    decision = SafetyGate(clinical_config.safety_rules).evaluate(state)
    assert decision.status == SafetyStatus.TRIGGERED
    assert decision.triggered_rule_ids == ["WARN-NEUROLOGICAL"]


def test_denial_does_not_trigger(clinical_config, state) -> None:
    state.merge_observation(_observation("safety.neurological", FieldStatus.DENIED, False))
    decision = SafetyGate(clinical_config.safety_rules).evaluate(state)
    assert decision.status == SafetyStatus.PENDING
    assert not decision.triggered_rule_ids


def test_first_ambiguity_requests_clarification(clinical_config, state) -> None:
    state.merge_observation(_observation("safety.respiratory", FieldStatus.NEEDS_CLARIFICATION))
    decision = SafetyGate(clinical_config.safety_rules).evaluate(state)
    assert decision.requires_clarification is True
    assert decision.clarification_field == "safety.respiratory"


def test_repeated_safety_ambiguity_conservatively_escalates(clinical_config, state) -> None:
    state.merge_observation(_observation("safety.respiratory", FieldStatus.NEEDS_CLARIFICATION))
    state.clarification_counts["safety.respiratory"] = 1
    decision = SafetyGate(clinical_config.safety_rules).evaluate(state)
    assert decision.status == SafetyStatus.TRIGGERED
    assert decision.triggered_rule_ids == ["WARN-RESPIRATORY-AMBIGUOUS"]
