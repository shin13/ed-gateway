from pathlib import Path
from uuid import uuid4

import pytest

from ed_gateway.application.configuration import ClinicalConfig, load_clinical_config
from ed_gateway.domain.models import InterviewPhase, InterviewState


@pytest.fixture
def clinical_config() -> ClinicalConfig:
    return load_clinical_config(Path(__file__).parents[1] / "config")


@pytest.fixture
def state() -> InterviewState:
    return InterviewState(session_id=uuid4(), phase=InterviewPhase.RESPONDENT)
