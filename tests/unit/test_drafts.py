from pathlib import Path

import pytest

from ed_gateway.application.drafts import DISCLAIMER, DraftGenerator
from ed_gateway.domain.models import FieldStatus, InformationSource, Observation


def test_draft_is_deterministic_and_preserves_provenance(clinical_config, state) -> None:
    state.merge_observation(
        Observation(
            field_key="symptom.chief_complaint",
            verbatim_text="我今天頭很暈",
            normalized_value={"label": "dizziness", "summary": "我今天頭很暈"},
            source=InformationSource.CAREGIVER_STATEMENT,
            status=FieldStatus.CONFIRMED,
            ai_normalized=True,
        )
    )
    generator = DraftGenerator(clinical_config, Path(__file__).parents[2] / "config" / "nurse-draft-template.md")
    first = generator.generate(state)
    second = generator.generate(state)
    assert first.rendered_markdown == second.rendered_markdown
    assert "我今天頭很暈" in first.rendered_markdown
    assert "dizziness" in first.rendered_markdown
    assert "CAREGIVER_STATEMENT" in first.rendered_markdown
    assert "待檢傷護理師／院方系統確認" in first.rendered_markdown
    assert first.rendered_markdown.rstrip().endswith(DISCLAIMER)


def test_partial_draft_marks_missing_fields(clinical_config, state) -> None:
    generator = DraftGenerator(clinical_config, Path(__file__).parents[2] / "config" / "nurse-draft-template.md")
    draft = generator.generate(state)
    assert "未取得" in draft.rendered_markdown
    assert "symptom.chief_complaint" in draft.structured["missing_fields"]
    assert "safety.neurological" in draft.structured["missing_fields"]


def test_unknown_declined_and_not_obtained_remain_explicitly_missing(clinical_config, state) -> None:
    for field, status in (
        ("demographics.age", FieldStatus.UNKNOWN),
        ("medical.history", FieldStatus.DECLINED),
        ("vitals", FieldStatus.NOT_OBTAINED),
    ):
        state.merge_observation(
            Observation(
                field_key=field,
                verbatim_text=status.value,
                source=InformationSource.PATIENT_STATEMENT,
                status=status,
            )
        )
    draft = DraftGenerator(
        clinical_config,
        Path(__file__).parents[2] / "config" / "nurse-draft-template.md",
    ).generate(state)
    assert {"demographics.age", "medical.history", "vitals"}.issubset(draft.structured["missing_fields"])
    assert "資料更新時間（UTC）" in draft.rendered_markdown


def test_urgent_draft_requests_immediate_nurse_review(clinical_config, state) -> None:
    state.triggered_rule_ids = ["WARN-NEUROLOGICAL"]
    generator = DraftGenerator(clinical_config, Path(__file__).parents[2] / "config" / "nurse-draft-template.md")
    draft = generator.generate(state)
    assert "請立即呼叫檢傷護理師" in draft.rendered_markdown
    assert "WARN-NEUROLOGICAL" in draft.rendered_markdown


def test_draft_template_is_validated_at_startup(clinical_config, tmp_path: Path) -> None:
    invalid_template = tmp_path / "draft.md"
    invalid_template.write_text("# incomplete", encoding="utf-8")
    with pytest.raises(ValueError, match="missing required sections"):
        DraftGenerator(clinical_config, invalid_template)
