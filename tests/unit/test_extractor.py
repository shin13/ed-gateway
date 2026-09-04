import pytest

from ed_gateway.application.extractor import ResponseExtractor
from ed_gateway.domain.models import FieldStatus, InformationSource, RespondentType
from ed_gateway.llm.mock import MockLLMClient


@pytest.fixture
def extractor() -> ResponseExtractor:
    return ResponseExtractor(MockLLMClient())


@pytest.mark.parametrize(
    ("text", "expected_status"),
    [("不知道", FieldStatus.UNKNOWN), ("跳過", FieldStatus.DECLINED), ("不方便回答", FieldStatus.DECLINED)],
)
async def test_special_answer_states(extractor, state, text, expected_status) -> None:
    observations = await extractor.extract(text=text, expected_field="symptom.onset", state=state)
    assert observations[-1].status == expected_status


async def test_family_history_is_not_current_neurological_warning(extractor, state) -> None:
    observations = await extractor.extract(
        text="我爸爸中風過，我很擔心",
        expected_field="safety.neurological",
        state=state,
    )
    assert any(item.field_key == "medical.family_history" for item in observations)
    assert not any(
        item.field_key == "safety.neurological"
        and item.status == FieldStatus.CONFIRMED
        and item.normalized_value == {"present": True}
        for item in observations
    )


async def test_past_fainting_is_not_current_warning(extractor, state) -> None:
    observations = await extractor.extract(
        text="我以前昏倒過",
        expected_field="safety.neurological",
        state=state,
    )
    assert any(item.field_key == "medical.history" for item in observations)
    assert not any(
        item.field_key == "safety.neurological" and item.status == FieldStatus.CONFIRMED for item in observations
    )


async def test_hypothetical_is_not_a_current_symptom(extractor, state) -> None:
    observations = await extractor.extract(
        text="如果胸痛會怎麼辦？",
        expected_field="symptom.chief_complaint",
        state=state,
    )
    assert any(item.field_key == "interaction.hypothetical_question" for item in observations)
    assert not any(item.field_key == "safety.cardiovascular" for item in observations)


async def test_current_neurological_statement_is_detected(extractor, state) -> None:
    observations = await extractor.extract(
        text="我現在突然半邊無力，講話也不清楚",
        expected_field="symptom.chief_complaint",
        state=state,
    )
    warning = next(item for item in observations if item.field_key == "safety.neurological")
    assert warning.status == FieldStatus.CONFIRMED
    assert warning.normalized_value["present"] is True


async def test_explicit_denial_is_preserved(extractor, state) -> None:
    observations = await extractor.extract(
        text="完全沒有胸痛或胸悶",
        expected_field="safety.cardiovascular",
        state=state,
    )
    observation = observations[-1]
    assert observation.status == FieldStatus.DENIED
    assert observation.normalized_value == {"present": False}


async def test_mixed_denial_and_current_warning_are_evaluated_per_clause(extractor, state) -> None:
    observations = await extractor.extract(
        text="沒有胸痛，但現在突然半邊無力",
        expected_field="safety.cardiovascular",
        state=state,
    )
    cardiovascular = next(item for item in observations if item.field_key == "safety.cardiovascular")
    neurological = next(item for item in observations if item.field_key == "safety.neurological")
    assert cardiovascular.status == FieldStatus.DENIED
    assert neurological.status == FieldStatus.CONFIRMED
    assert neurological.normalized_value["present"] is True


async def test_caregiver_source_is_preserved(extractor, state) -> None:
    state.respondent_type = RespondentType.CAREGIVER
    observations = await extractor.extract(
        text="他從早上開始頭暈",
        expected_field="symptom.onset",
        state=state,
    )
    assert observations[-1].source == InformationSource.CAREGIVER_STATEMENT


async def test_respondent_choice_sets_caregiver_provenance(extractor, state) -> None:
    observations = await extractor.extract(
        text="我是陪同家屬",
        expected_field="respondent.type",
        state=state,
    )
    assert observations[-1].source == InformationSource.CAREGIVER_STATEMENT


async def test_live_provider_can_resolve_ambiguous_non_safety_value(state) -> None:
    class ProposalLLM:
        async def extract(self, **_kwargs):
            return {
                "classification": "current",
                "normalized_value": 34,
                "status": "CONFIRMED",
                "requires_human_confirmation": False,
            }

    observations = await ResponseExtractor(ProposalLLM()).extract(
        text="三十四歲",
        expected_field="demographics.age",
        state=state,
    )
    assert observations[-1].status == FieldStatus.CONFIRMED
    assert observations[-1].normalized_value == 34


async def test_live_provider_cannot_clear_ambiguous_safety_answer(state) -> None:
    class UnsafeNegativeProposalLLM:
        async def extract(self, **_kwargs):
            return {
                "classification": "denial",
                "normalized_value": {"present": False},
                "status": "DENIED",
                "requires_human_confirmation": False,
            }

    observations = await ResponseExtractor(UnsafeNegativeProposalLLM()).extract(
        text="胸口怪怪的",
        expected_field="safety.cardiovascular",
        state=state,
    )
    assert observations[-1].status == FieldStatus.NEEDS_CLARIFICATION


async def test_live_provider_cannot_set_unrecognized_respondent_type(state) -> None:
    class FreeformRespondentTypeLLM:
        async def extract(self, **_kwargs):
            return {
                "classification": "current",
                "normalized_value": "patient self-report",
                "status": "CONFIRMED",
                "requires_human_confirmation": False,
            }

    observations = await ResponseExtractor(FreeformRespondentTypeLLM()).extract(
        text="I am the patient myself.",
        expected_field="respondent.type",
        state=state,
    )
    assert observations[-1].status == FieldStatus.NEEDS_CLARIFICATION


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("胸口不舒服", "chest_discomfort"),
        ("頭暈會轉", "dizziness"),
        ("今天發燒", "fever"),
        ("搬東西後腰痛", "lower_back_pain"),
    ],
)
async def test_reference_complaints_share_one_normalizer(extractor, state, text, label) -> None:
    observations = await extractor.extract(
        text=text,
        expected_field="symptom.chief_complaint",
        state=state,
    )
    complaint = next(item for item in observations if item.field_key == "symptom.chief_complaint")
    assert complaint.normalized_value["label"] == label


async def test_unmeasured_vitals_are_not_estimated(extractor, state) -> None:
    observations = await extractor.extract(
        text="我沒量血壓，大概一百三吧",
        expected_field="vitals",
        state=state,
    )
    assert observations[-1].status == FieldStatus.NOT_OBTAINED
    assert observations[-1].normalized_value is None


async def test_clinician_vitals_preserve_measurement_source_and_time(extractor, state) -> None:
    observations = await extractor.extract(
        text="護理師量今天早上9點血壓 128/76，血氧 98%",
        expected_field="vitals",
        state=state,
    )
    observation = observations[-1]
    assert observation.source == InformationSource.CLINICIAN_MEASUREMENT
    assert observation.normalized_value["blood_pressure_mm_hg"] == {"systolic": 128, "diastolic": 76}
    assert observation.normalized_value["spo2_percent"] == 98
    assert observation.normalized_value["measurement_time_text"] == "今天早上9點"
