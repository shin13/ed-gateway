from __future__ import annotations

from pathlib import Path
from string import Formatter
from typing import Any

from ed_gateway.application.configuration import ClinicalConfig
from ed_gateway.domain.models import DraftPayload, FieldStatus, InterviewState, Observation

DISCLAIMER = "此為護理紀錄草稿，須由檢傷護理師確認後方可使用。"
TEMPLATE_FIELDS = {
    "updated_at_utc",
    "interaction_mode",
    "respondent",
    "safety",
    "demographics",
    "arrival",
    "tocc",
    "chief_complaint",
    "timeline",
    "vitals",
    "pain",
    "symptom_details",
    "trauma",
    "function",
    "history",
    "missing_and_conflicts",
    "review_points",
}


class DraftGenerator:
    def __init__(self, config: ClinicalConfig, template_path: Path | None = None) -> None:
        self._config = config
        self._template_path = (
            template_path or Path(__file__).resolve().parents[3] / "config" / "nurse-draft-template.md"
        )
        self._template = self._template_path.read_text(encoding="utf-8")
        missing_sections = [
            section
            for section in self._config.interview_schema.required_draft_sections
            if f"【{section}】" not in self._template
        ]
        if missing_sections:
            raise ValueError(f"draft template is missing required sections: {missing_sections}")
        placeholders = {
            field_name for _, field_name, _, _ in Formatter().parse(self._template) if field_name is not None
        }
        if placeholders != TEMPLATE_FIELDS:
            raise ValueError(
                f"draft template placeholders mismatch; missing={TEMPLATE_FIELDS - placeholders}, "
                f"unknown={placeholders - TEMPLATE_FIELDS}"
            )
        if not self._template.rstrip().endswith(DISCLAIMER):
            raise ValueError("draft template is missing the required disclaimer")

    def generate(self, state: InterviewState, revision: int = 1) -> DraftPayload:
        all_fields = set(self._config.interview_schema.observation_fields)
        incomplete_statuses = {
            FieldStatus.NOT_OBTAINED,
            FieldStatus.UNKNOWN,
            FieldStatus.DECLINED,
            FieldStatus.NEEDS_CLARIFICATION,
        }
        state.missing_fields = sorted(
            field
            for field in all_fields
            if field not in state.observations or state.observations[field].status in incomplete_statuses
        )
        structured = {
            "session_id": str(state.session_id),
            "phase": state.phase.value,
            "rule_version": state.rule_version,
            "safety_status": state.safety_status.value,
            "triggered_rule_ids": state.triggered_rule_ids,
            "observations": {key: value.model_dump(mode="json") for key, value in state.observations.items()},
            "observation_history": [item.model_dump(mode="json") for item in state.observation_history],
            "missing_fields": state.missing_fields,
            "contradictions": state.contradictions,
        }
        markdown = self._render(state)
        if not markdown.rstrip().endswith(DISCLAIMER):
            raise ValueError("draft is missing the required disclaimer")
        return DraftPayload(revision=revision, structured=structured, rendered_markdown=markdown)

    def _render(self, state: InterviewState) -> str:
        safety_count = sum(1 for key in state.observations if key.startswith("safety."))
        trigger_text = "、".join(state.triggered_rule_ids) if state.triggered_rule_ids else "未觸發"
        safety = f"警訊覆蓋：{safety_count}/12；觸發規則：{trigger_text}"
        if state.triggered_rule_ids:
            safety = "請立即呼叫檢傷護理師。" + safety

        values = {
            "updated_at_utc": state.updated_at.isoformat(),
            "interaction_mode": f"{state.interaction_mode.value}；回答語言：{state.answer_language}",
            "respondent": self._show(state.observations.get("respondent.type")),
            "safety": safety,
            "demographics": f"年齡：{self._show(state.observations.get('demographics.age'))}",
            "arrival": self._show(state.observations.get("arrival.source")),
            "tocc": self._show(state.observations.get("tocc.exposure")),
            "chief_complaint": self._chief_complaint(state.observations.get("symptom.chief_complaint")),
            "timeline": self._join(
                state,
                [
                    "symptom.onset",
                    "symptom.duration",
                    "symptom.timing",
                    "symptom.onset_mode",
                    "symptom.course",
                    "symptom.recent_change",
                ],
            ),
            "vitals": self._show(state.observations.get("vitals")),
            "pain": self._join(state, ["symptom.location", "symptom.severity", "symptom.radiation"]),
            "symptom_details": self._join(
                state,
                [
                    "symptom.quality",
                    "symptom.associated",
                    "symptom.aggravating_factors",
                    "symptom.relieving_factors",
                ],
            ),
            "trauma": self._show(state.observations.get("symptom.trauma_context")),
            "function": self._show(state.observations.get("symptom.functional_impact")),
            "history": self._join(
                state, ["medical.history", "medical.family_history", "medications.current", "allergies"]
            ),
            "missing_and_conflicts": self._missing_and_conflicts(state),
            "review_points": self._review_points(state),
        }
        return self._template.format(**values)

    @staticmethod
    def _show(observation: Observation | None) -> str:
        if observation is None:
            return "未取得"
        labels = {
            FieldStatus.NOT_OBTAINED: "未取得",
            FieldStatus.UNKNOWN: "不知道／不確定",
            FieldStatus.DECLINED: "拒絕回答／已跳過",
            FieldStatus.NEEDS_CLARIFICATION: "待澄清",
        }
        if observation.status in labels:
            return f"{labels[observation.status]}（原文：「{observation.verbatim_text}」）"
        value: Any = observation.normalized_value
        rendered = str(value) if value is not None else observation.status.value
        return f"{rendered}（原文：「{observation.verbatim_text}」；來源：{observation.source.value}）"

    def _join(self, state: InterviewState, fields: list[str]) -> str:
        parts = [f"{field}：{self._show(state.observations.get(field))}" for field in fields]
        return "\n".join(parts)

    @staticmethod
    def _chief_complaint(observation: Observation | None) -> str:
        if observation is None:
            return "未取得"
        normalized = observation.normalized_value
        label = normalized.get("label", "other") if isinstance(normalized, dict) else "other"
        return f"原話：「{observation.verbatim_text}」\n正規化標籤：{label}\n來源：{observation.source.value}"

    @staticmethod
    def _missing_and_conflicts(state: InterviewState) -> str:
        missing = "、".join(state.missing_fields) if state.missing_fields else "無"
        conflicts = "；".join(state.contradictions) if state.contradictions else "無"
        return f"未取得：{missing}\n矛盾：{conflicts}"

    @staticmethod
    def _review_points(state: InterviewState) -> str:
        if state.triggered_rule_ids:
            return "立即確認警訊、觸發原話、發生時間與尚未取得的關鍵資料。"
        return "確認原話、正規化內容、資料來源、缺失欄位與矛盾資料。"
