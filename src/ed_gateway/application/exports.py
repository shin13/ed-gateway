from __future__ import annotations

from ed_gateway.application.drafts import DISCLAIMER
from ed_gateway.domain.models import DraftPayload, InterviewState, TranscriptMessage

ROLE_LABELS = {"assistant": "系統", "user": "填答者"}
NO_DRAFT = "本次會談未產生草稿。"
NO_TRANSCRIPT = "（無對話紀錄）"


def render_session_export(
    *,
    state: InterviewState,
    transcript: list[TranscriptMessage],
    draft: DraftPayload | None,
    llm_provider: str,
    llm_model: str,
) -> str:
    """Render one session as a self-contained Markdown file for tester feedback."""
    sections = [
        _header(state, llm_provider, llm_model),
        _transcript_section(transcript),
        _draft_section(draft),
        DISCLAIMER,
    ]
    return "\n\n".join(sections) + "\n"


def _header(state: InterviewState, llm_provider: str, llm_model: str) -> str:
    lines = [
        "# ED Gateway 對話匯出（研究展示用途｜僅使用合成資料）",
        "",
        f"- 會談編號：{state.session_id}",
        f"- 建立時間（UTC）：{state.created_at:%Y-%m-%d %H:%M:%S}",
        f"- 最後更新（UTC）：{state.updated_at:%Y-%m-%d %H:%M:%S}",
        f"- 語言模型：{llm_provider} / {llm_model or '（未設定）'}",
        f"- 警訊規則版本：{state.rule_version}",
        f"- 目前階段：{state.phase.value}",
        f"- 警訊狀態：{state.safety_status.value}",
        f"- 觸發警訊：{'、'.join(state.triggered_rule_ids) or '無'}",
    ]
    return "\n".join(lines)


def _transcript_section(transcript: list[TranscriptMessage]) -> str:
    if not transcript:
        return f"## 對話逐字紀錄\n\n{NO_TRANSCRIPT}"
    lines = ["## 對話逐字紀錄", ""]
    lines += [
        f"{message.sequence}. **{ROLE_LABELS.get(message.role, message.role)}**"
        f"（{message.source}）：{message.content}"
        for message in transcript
    ]
    return "\n".join(lines)


def _draft_section(draft: DraftPayload | None) -> str:
    return f"## 護理紀錄草稿\n\n{draft.rendered_markdown if draft else NO_DRAFT}"
