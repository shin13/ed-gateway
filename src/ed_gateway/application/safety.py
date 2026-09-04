from ed_gateway.application.configuration import SafetyRuleDefinition
from ed_gateway.domain.models import FieldStatus, InterviewState, SafetyDecision, SafetyStatus


class SafetyGate:
    def __init__(self, rules: list[SafetyRuleDefinition]) -> None:
        self._rules = rules

    def evaluate(self, state: InterviewState) -> SafetyDecision:
        triggered: list[str] = []
        for rule in self._rules:
            observation = state.observations.get(rule.observation_field)
            if not observation:
                continue
            value = observation.normalized_value
            present = isinstance(value, dict) and value.get("present") is True
            if observation.status.value in rule.trigger_statuses and present:
                triggered.append(rule.id)

        if triggered:
            return SafetyDecision(status=SafetyStatus.TRIGGERED, triggered_rule_ids=triggered)

        for rule in self._rules:
            observation = state.observations.get(rule.observation_field)
            if not observation or observation.status not in {
                FieldStatus.NEEDS_CLARIFICATION,
                FieldStatus.UNKNOWN,
            }:
                continue
            attempts = state.clarification_counts.get(rule.observation_field, 0)
            if attempts >= 1:
                return SafetyDecision(
                    status=SafetyStatus.TRIGGERED,
                    triggered_rule_ids=[f"{rule.id}-AMBIGUOUS"],
                )
            return SafetyDecision(
                status=SafetyStatus.PENDING,
                requires_clarification=True,
                clarification_field=rule.observation_field,
            )

        safety_fields = {rule.observation_field for rule in self._rules}
        covered = safety_fields.intersection(state.observations)
        status = SafetyStatus.CLEAR if covered == safety_fields else SafetyStatus.PENDING
        return SafetyDecision(status=status)
