import httpx

from ed_gateway.application.repository import InMemoryInterviewRepository
from ed_gateway.bootstrap import create_orchestrator
from ed_gateway.domain.models import CreateSessionRequest
from ed_gateway.settings import Settings


class _FailingLLM:
    async def extract(self, **_kwargs):
        raise httpx.ReadTimeout("provider timed out")


async def test_provider_failure_completes_the_turn_and_records_it(monkeypatch) -> None:
    monkeypatch.setattr("ed_gateway.bootstrap.create_llm_client", lambda settings: _FailingLLM())
    repository = InMemoryInterviewRepository()
    orchestrator = create_orchestrator(
        repository=repository,
        settings=Settings(APP_ENV="test", LLM_PROVIDER="mock", _env_file=None),
    )
    started = await orchestrator.create_session(CreateSessionRequest())

    turn = await orchestrator.handle_message(started.session_id, "我是病人本人")

    assert turn.patient_message
    state = await orchestrator.get_state(started.session_id)
    assert state.safety_scan_degraded == ["我是病人本人"]
