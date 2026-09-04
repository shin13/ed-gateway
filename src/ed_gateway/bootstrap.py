from __future__ import annotations

from pathlib import Path

from ed_gateway.application.configuration import load_clinical_config
from ed_gateway.application.drafts import DraftGenerator
from ed_gateway.application.extractor import ResponseExtractor
from ed_gateway.application.orchestrator import InterviewOrchestrator
from ed_gateway.application.planner import QuestionPlanner
from ed_gateway.application.repository import InterviewRepository
from ed_gateway.application.safety import SafetyGate
from ed_gateway.application.session_manager import InterviewSessionManager
from ed_gateway.llm.base import LLMClient
from ed_gateway.llm.mock import MockLLMClient
from ed_gateway.llm.openai_compatible import OpenAICompatibleClient
from ed_gateway.settings import Settings


def create_llm_client(settings: Settings) -> LLMClient:
    if settings.LLM_PROVIDER == "mock":
        return MockLLMClient()
    return OpenAICompatibleClient(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY.get_secret_value(),
        model=settings.LLM_MODEL,
        timeout=settings.LLM_TIMEOUT_SECONDS,
        max_retries=settings.LLM_MAX_RETRIES,
        temperature=settings.LLM_TEMPERATURE,
    )


def create_orchestrator(
    *, repository: InterviewRepository, settings: Settings, project_root: Path | None = None
) -> InterviewOrchestrator:
    root = project_root or Path(__file__).resolve().parents[2]
    config = load_clinical_config(root / "config")
    return InterviewOrchestrator(
        repository=repository,
        session_manager=InterviewSessionManager(repository, config.safety_version),
        extractor=ResponseExtractor(create_llm_client(settings)),
        safety_gate=SafetyGate(config.safety_rules),
        planner=QuestionPlanner(config),
        draft_generator=DraftGenerator(config, root / "config" / "nurse-draft-template.md"),
    )
