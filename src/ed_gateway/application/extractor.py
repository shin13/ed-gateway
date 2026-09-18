from __future__ import annotations

import re
from typing import Any

from ed_gateway.domain.models import (
    FieldStatus,
    InformationSource,
    InterviewState,
    Observation,
    RespondentType,
)
from ed_gateway.llm.base import LLMClient

SKIP_WORDS = {"跳過", "略過", "不回答"}
UNKNOWN_WORDS = {"不知道", "不清楚", "不確定", "無法確認"}
DECLINE_WORDS = {"拒絕", "不想回答", "不方便回答"}
NEGATIONS = ("沒有", "並無", "不會", "沒有任何", "否認", "都沒有", "完全沒有")
POSITIVE_SHORT = {"有", "會", "是", "對", "有的", "會的"}
FAMILY_MARKERS = ("爸爸", "父親", "媽媽", "母親", "家人", "家族", "哥哥", "姐姐", "弟弟", "妹妹")
PAST_MARKERS = ("以前", "過去", "上次", "曾經", "小時候", "病史")
HYPOTHETICAL_MARKERS = ("如果", "假如", "會不會是", "算不算", "這樣算", "怎麼辦", "嗎？", "嗎?")
CLAUSE_SPLIT = re.compile(r"[，,。；;！？!?]|\s*(?:但是|但|可是|不過)\s*")

SAFETY_CONCEPTS: dict[str, tuple[str, ...]] = {
    "safety.cardiovascular": ("胸痛", "胸悶", "胸口痛", "胸口悶", "胸口很悶"),
    "safety.neurological": (
        "臉歪",
        "半邊無力",
        "單側無力",
        "手腳無力",
        "說話不清",
        "看不到",
        "複視",
        "站不穩",
        "最痛的頭痛",
        "抽搐",
        "叫不醒",
        "意識不清",
        "昏倒",
    ),
    "safety.respiratory": ("喘到說不出話", "嘴唇發紫", "呼吸困難", "喉嚨腫", "氣管被塞"),
    "safety.circulation": ("快昏倒", "眼前發黑", "皮膚冰冷", "臉色蒼白", "心悸又無力"),
    "safety.bleeding": ("止不住的血", "吐血", "黑便", "大量血便", "大量陰道出血"),
    "safety.allergy": ("全身起疹", "嘴唇腫", "喉嚨腫", "嚴重過敏"),
    "safety.infection_temperature": ("發燒又意識不清", "發燒又很喘", "發燒且意識不清"),
    "safety.severe_pain": ("痛到十分", "疼痛十分", "劇烈疼痛", "突然持續腹痛"),
    "safety.trauma": ("被甩出", "翻車", "槍傷", "穿刺傷", "高處墜落", "受困"),
    "safety.hypertensive": ("血壓兩百", "血壓200"),
    "safety.mental_health": ("想死", "不想活", "傷害自己", "傷害別人", "無法冷靜"),
    "safety.self_identified_danger": ("快撐不住", "快不行", "情況很危險"),
}


def _source_for(state: InterviewState) -> InformationSource:
    if state.respondent_type == RespondentType.CAREGIVER:
        return InformationSource.CAREGIVER_STATEMENT
    return InformationSource.PATIENT_STATEMENT


def _special_status(text: str) -> FieldStatus | None:
    compact = text.strip().replace("。", "")
    if compact in SKIP_WORDS:
        return FieldStatus.DECLINED
    if compact in UNKNOWN_WORDS:
        return FieldStatus.UNKNOWN
    if compact in DECLINE_WORDS:
        return FieldStatus.DECLINED
    return None


def _is_negated(text: str) -> bool:
    return any(token in text for token in NEGATIONS)


def _clauses(text: str) -> list[str]:
    return [clause.strip() for clause in CLAUSE_SPLIT.split(text) if clause.strip()]


def _classify_statement(text: str) -> str:
    if any(marker in text for marker in FAMILY_MARKERS):
        return "family_history"
    if any(marker in text for marker in PAST_MARKERS):
        return "past_history"
    if any(marker in text for marker in HYPOTHETICAL_MARKERS):
        return "hypothetical"
    clauses = _clauses(text)
    if clauses and all(_is_negated(clause) for clause in clauses):
        return "denial"
    return "current"


def _complaint_label(text: str) -> str:
    lowered = text.lower()
    if any(value in lowered for value in ("胸痛", "胸悶", "胸口悶", "胸口不舒服")):
        return "chest_discomfort"
    if any(value in lowered for value in ("頭暈", "眩暈", "天旋地轉")):
        return "dizziness"
    if any(value in lowered for value in ("發燒", "發熱", "燒起來")):
        return "fever"
    if any(value in lowered for value in ("下背痛", "下背疼", "腰痛", "腰疼")):
        return "lower_back_pain"
    return "other"


def _measurement_source(text: str, fallback: InformationSource) -> InformationSource:
    if any(marker in text for marker in ("護理師量", "醫師量", "醫院量", "院方量")):
        return InformationSource.CLINICIAN_MEASUREMENT
    if any(marker in text for marker in ("血壓機", "血氧機", "體溫計", "手錶", "機器量")):
        return InformationSource.DEVICE_MEASUREMENT
    return fallback


def _normalize_vitals(text: str) -> dict[str, Any]:
    normalized: dict[str, Any] = {"reported_text": text, "measurement_time_text": None}
    patterns: tuple[tuple[str, str], ...] = (
        ("blood_pressure_mm_hg", r"(?<!\d)(\d{2,3})\s*[/／]\s*(\d{2,3})(?!\d)"),
        ("pulse_bpm", r"(?:脈搏|心跳)[^\d]{0,5}(\d{2,3})"),
        ("temperature_c", r"(?:體溫|溫度)[^\d]{0,5}(\d{2}(?:\.\d)?)"),
        ("spo2_percent", r"(?:血氧|SpO2|SPO2)[^\d]{0,5}(\d{2,3})\s*%?"),
        ("glucose_mg_dl", r"(?:血糖)[^\d]{0,5}(\d{2,3})"),
    )
    for key, pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        if key == "blood_pressure_mm_hg":
            normalized[key] = {"systolic": int(match.group(1)), "diastolic": int(match.group(2))}
        else:
            value = float(match.group(1)) if "." in match.group(1) else int(match.group(1))
            normalized[key] = value
    time_match = re.search(r"(?:今天|昨天)?(?:早上|上午|中午|下午|晚上)?\s*\d{1,2}(?::\d{2}|點(?:半|\d{1,2}分)?)", text)
    if time_match:
        normalized["measurement_time_text"] = time_match.group(0).strip()
    return normalized


class ResponseExtractor:
    """Context-aware extractor with optional LLM assistance and deterministic safeguards."""

    def __init__(self, llm: LLMClient, safety_categories: dict[str, list[str]] | None = None) -> None:
        self._llm = llm
        self._safety_categories = safety_categories or {}

    async def extract(self, *, text: str, expected_field: str, state: InterviewState) -> list[Observation]:
        source = _source_for(state)
        special_status = _special_status(text)
        if special_status is not None:
            return [
                Observation(
                    field_key=expected_field,
                    verbatim_text=text,
                    source=source,
                    status=special_status,
                    requires_human_confirmation=expected_field.startswith("safety."),
                )
            ]

        classification = _classify_statement(text)
        observations: list[Observation] = []

        if classification == "family_history":
            observations.append(
                Observation(
                    field_key="medical.family_history",
                    verbatim_text=text,
                    normalized_value=text,
                    source=source,
                    status=FieldStatus.CONFIRMED,
                )
            )
        elif classification == "past_history":
            observations.append(
                Observation(
                    field_key="medical.history",
                    verbatim_text=text,
                    normalized_value=text,
                    source=source,
                    status=FieldStatus.CONFIRMED,
                )
            )
        elif classification == "hypothetical":
            observations.append(
                Observation(
                    field_key="interaction.hypothetical_question",
                    verbatim_text=text,
                    normalized_value=text,
                    source=source,
                    status=FieldStatus.NEEDS_CLARIFICATION,
                    requires_human_confirmation=True,
                )
            )

        observations.extend(self._detect_current_safety(text, source, expected_field))

        expected = self._extract_expected(text, expected_field, source, classification)
        if expected and not any(item.field_key == expected.field_key for item in observations):
            observations.append(expected)

        # The provider may resolve an otherwise ambiguous field. Safety-negative proposals never clear a warning.
        proposal = await self._llm.extract(
            text=text,
            expected_field=expected_field,
            context={
                "respondent_type": state.respondent_type.value,
                "classification": classification,
                "safety_categories": self._safety_categories,
            },
        )
        provider_observation = self._provider_observation(
            proposal=proposal,
            text=text,
            expected_field=expected_field,
            source=source,
        )
        if provider_observation is not None:
            existing_index = next(
                (index for index, item in enumerate(observations) if item.field_key == expected_field),
                None,
            )
            if existing_index is None:
                observations.append(provider_observation)
            elif observations[existing_index].status == FieldStatus.NEEDS_CLARIFICATION:
                observations[existing_index] = provider_observation

        observations.extend(
            self._proposed_safety_observations(
                proposal=proposal,
                text=text,
                expected_field=expected_field,
                source=source,
                observations=observations,
            )
        )
        return observations

    def _proposed_safety_observations(
        self,
        *,
        proposal: dict[str, Any],
        text: str,
        expected_field: str,
        source: InformationSource,
        observations: list[Observation],
    ) -> list[Observation]:
        """Add-only: a proposal may flag a category the keyword sweep missed, never clear one."""
        proposed = proposal.get("other_safety_categories")
        if not isinstance(proposed, list):
            return []
        seen = {item.field_key for item in observations} | {expected_field}
        additions: list[Observation] = []
        for field in proposed:
            if not isinstance(field, str) or field not in self._safety_categories or field in seen:
                continue
            seen.add(field)
            additions.append(
                Observation(
                    field_key=field,
                    verbatim_text=text,
                    normalized_value={"present": True, "detected_by": "llm_semantic_screen"},
                    source=source,
                    status=FieldStatus.CONFIRMED,
                    ai_normalized=True,
                    requires_human_confirmation=True,
                )
            )
        return additions

    def _extract_expected(
        self,
        text: str,
        expected_field: str,
        source: InformationSource,
        classification: str,
    ) -> Observation | None:
        if expected_field == "respondent.type":
            if any(token in text for token in ("家屬", "陪同", "照顧者")):
                value = RespondentType.CAREGIVER.value
                source = InformationSource.CAREGIVER_STATEMENT
            elif any(token in text for token in ("本人", "病人", "自己")):
                value = RespondentType.PATIENT.value
                source = InformationSource.PATIENT_STATEMENT
            else:
                return self._ambiguous(expected_field, text, source)
            return Observation(
                field_key=expected_field,
                verbatim_text=text,
                normalized_value=value,
                source=source,
                status=FieldStatus.CONFIRMED,
                ai_normalized=True,
            )

        if expected_field == "demographics.age":
            match = re.search(r"(?<!\d)(\d{1,3})(?!\d)", text)
            if not match:
                return self._ambiguous(expected_field, text, source)
            age = int(match.group(1))
            if not 0 <= age <= 125:
                return self._ambiguous(expected_field, text, source)
            return Observation(
                field_key=expected_field,
                verbatim_text=text,
                normalized_value=age,
                source=source,
                status=FieldStatus.CONFIRMED,
                ai_normalized=True,
            )

        if expected_field.startswith("safety."):
            if classification in {"family_history", "past_history", "hypothetical"}:
                return self._ambiguous(expected_field, text, source)
            polarity = self._safety_polarity(text, SAFETY_CONCEPTS.get(expected_field, ()))
            if polarity is False:
                return Observation(
                    field_key=expected_field,
                    verbatim_text=text,
                    normalized_value={"present": False},
                    source=source,
                    status=FieldStatus.DENIED,
                    ai_normalized=True,
                )
            if polarity is True:
                return Observation(
                    field_key=expected_field,
                    verbatim_text=text,
                    normalized_value={"present": True, "detail": text},
                    source=source,
                    status=FieldStatus.CONFIRMED,
                    ai_normalized=True,
                )
            return self._ambiguous(expected_field, text, source)

        if classification == "hypothetical":
            return self._ambiguous(expected_field, text, source)

        normalized: Any = text
        ai_normalized = False
        if expected_field == "symptom.chief_complaint":
            normalized = {"label": _complaint_label(text), "summary": text}
            ai_normalized = True
        elif expected_field == "symptom.severity":
            match = re.search(r"(?<!\d)(10|[0-9])(?!\d)", text)
            normalized = (
                {"value": int(match.group(1)), "method": "0-10 numeric scale"}
                if match
                else {"description": text, "method": "verbal description"}
            )
            ai_normalized = True
        elif expected_field.startswith("vitals") and any(marker in text for marker in ("沒量", "未量", "沒有量")):
            return Observation(
                field_key=expected_field,
                verbatim_text=text,
                normalized_value=None,
                source=source,
                status=FieldStatus.NOT_OBTAINED,
            )
        elif expected_field.startswith("vitals"):
            normalized = _normalize_vitals(text)
            source = _measurement_source(text, source)
            ai_normalized = True

        status = FieldStatus.DENIED if classification == "denial" else FieldStatus.CONFIRMED
        return Observation(
            field_key=expected_field,
            verbatim_text=text,
            normalized_value=normalized,
            source=source,
            status=status,
            ai_normalized=ai_normalized,
        )

    @staticmethod
    def _ambiguous(field: str, text: str, source: InformationSource) -> Observation:
        return Observation(
            field_key=field,
            verbatim_text=text,
            normalized_value=None,
            source=source,
            status=FieldStatus.NEEDS_CLARIFICATION,
            requires_human_confirmation=True,
        )

    @staticmethod
    def _safety_polarity(text: str, concepts: tuple[str, ...]) -> bool | None:
        relevant_clauses = [clause for clause in _clauses(text) if any(concept in clause for concept in concepts)]
        if relevant_clauses:
            if any(not _is_negated(clause) for clause in relevant_clauses):
                return True
            return False
        compact = text.strip().replace("。", "")
        if compact in POSITIVE_SHORT:
            return True
        if _is_negated(text):
            return False
        return None

    @staticmethod
    def _detect_current_safety(text: str, source: InformationSource, expected_field: str) -> list[Observation]:
        detected: list[Observation] = []
        for clause in _clauses(text):
            if _classify_statement(clause) != "current" or _is_negated(clause):
                continue
            for field, concepts in SAFETY_CONCEPTS.items():
                if field == expected_field:
                    continue
                matches = [concept for concept in concepts if concept in clause]
                if matches:
                    detected.append(
                        Observation(
                            field_key=field,
                            verbatim_text=clause,
                            normalized_value={"present": True, "concepts": matches},
                            source=source,
                            status=FieldStatus.CONFIRMED,
                            ai_normalized=True,
                        )
                    )
        return detected

    @staticmethod
    def _provider_observation(
        *,
        proposal: dict[str, Any],
        text: str,
        expected_field: str,
        source: InformationSource,
    ) -> Observation | None:
        classification = proposal.get("classification")
        status_value = proposal.get("status")
        if not isinstance(classification, str) or not isinstance(status_value, str):
            return None
        try:
            status = FieldStatus(status_value.upper())
        except ValueError:
            return None

        normalized_value = proposal.get("normalized_value")
        if expected_field.startswith("safety."):
            is_current = classification.lower() in {"current", "current_symptom"}
            is_positive = isinstance(normalized_value, dict) and normalized_value.get("present") is True
            if status != FieldStatus.CONFIRMED or not is_current or not is_positive:
                return None
        elif expected_field == "respondent.type":
            if status == FieldStatus.CONFIRMED and (
                not isinstance(normalized_value, str)
                or normalized_value.strip().upper() not in {RespondentType.PATIENT, RespondentType.CAREGIVER}
            ):
                return None
            if isinstance(normalized_value, str):
                normalized_value = normalized_value.strip().upper()
        elif status == FieldStatus.CONFIRMED and normalized_value is None:
            return None

        return Observation(
            field_key=expected_field,
            verbatim_text=text,
            normalized_value=normalized_value,
            source=source,
            status=status,
            ai_normalized=True,
            requires_human_confirmation=bool(proposal.get("requires_human_confirmation", False)),
        )
