from ed_gateway.application.drafts import DISCLAIMER
from ed_gateway.application.exports import render_session_export
from ed_gateway.domain.models import DraftPayload, TranscriptMessage

TRANSCRIPT = [
    TranscriptMessage(sequence=1, role="assistant", content="現在操作的是病人本人，還是家屬？", source="SYSTEM"),
    TranscriptMessage(sequence=2, role="user", content="我是家屬", source="CAREGIVER_STATEMENT"),
]


def test_export_keeps_the_transcript_in_order_and_names_the_provider(state) -> None:
    state.triggered_rule_ids = ["WARN-CARDIOVASCULAR"]

    markdown = render_session_export(
        state=state,
        transcript=TRANSCRIPT,
        draft=None,
        llm_provider="mock",
        llm_model="",
    )

    assert str(state.session_id) in markdown
    assert "mock" in markdown
    assert state.rule_version in markdown
    assert "WARN-CARDIOVASCULAR" in markdown
    assert "CAREGIVER_STATEMENT" in markdown
    assert markdown.index("現在操作的是病人本人") < markdown.index("我是家屬")


def test_export_states_plainly_when_no_draft_was_generated(state) -> None:
    markdown = render_session_export(
        state=state,
        transcript=TRANSCRIPT,
        draft=None,
        llm_provider="openai_compatible",
        llm_model="gpt-4.1-mini",
    )

    assert "未產生草稿" in markdown
    assert "gpt-4.1-mini" in markdown


def test_export_embeds_the_draft_when_one_exists(state) -> None:
    draft = DraftPayload(revision=1, structured={}, rendered_markdown=f"【主訴】頭暈\n\n{DISCLAIMER}")

    markdown = render_session_export(
        state=state,
        transcript=TRANSCRIPT,
        draft=draft,
        llm_provider="mock",
        llm_model="",
    )

    assert "【主訴】頭暈" in markdown
    assert "未產生草稿" not in markdown


def test_export_always_ends_with_the_nurse_review_disclaimer(state) -> None:
    markdown = render_session_export(
        state=state,
        transcript=[],
        draft=None,
        llm_provider="mock",
        llm_model="",
    )

    assert markdown.rstrip().endswith(DISCLAIMER)


def test_multi_line_messages_do_not_break_the_transcript_layout(state) -> None:
    transcript = [
        TranscriptMessage(sequence=1, role="assistant", content="第一段\n\n第二段", source="SYSTEM"),
        TranscriptMessage(sequence=2, role="user", content="我是家屬", source="CAREGIVER_STATEMENT"),
    ]

    markdown = render_session_export(
        state=state,
        transcript=transcript,
        draft=None,
        llm_provider="mock",
        llm_model="",
    )

    assert "### 1. 系統（SYSTEM）" in markdown
    assert "### 2. 填答者（CAREGIVER_STATEMENT）" in markdown
    assert "第二段" in markdown
