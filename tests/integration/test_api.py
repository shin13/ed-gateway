from uuid import UUID

import httpx
import pytest

from ed_gateway.api.app import create_app
from ed_gateway.application.repository import InMemoryInterviewRepository
from ed_gateway.domain.models import CreateSessionRequest
from ed_gateway.settings import Settings


@pytest.fixture
def repository() -> InMemoryInterviewRepository:
    return InMemoryInterviewRepository()


@pytest.fixture
def app(repository):
    settings = Settings(APP_ENV="test", LLM_PROVIDER="mock", _env_file=None)
    return create_app(settings=settings, repository=repository)


@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as value:
        yield value


async def _create(client: httpx.AsyncClient) -> dict:
    response = await client.post("/api/v1/interview-sessions", json={})
    assert response.status_code == 201
    return response.json()


async def test_session_creation_has_required_starter(client, repository) -> None:
    turn = await _create(client)
    session_id = UUID(turn["session_id"])
    assert turn["phase"] == "RESPONDENT"
    assert turn["next_question_id"] == "respondent_type"
    assert "不會診斷" in turn["patient_message"]
    assert "病人本人，還是家屬或陪同者" in turn["patient_message"]
    assert session_id in repository.states


async def test_raw_message_is_saved_before_extraction(app, repository) -> None:
    class FailingExtractor:
        async def extract(self, **_kwargs):
            raise RuntimeError("synthetic extraction failure")

    turn = await app.state.orchestrator.create_session(CreateSessionRequest())
    app.state.orchestrator._extractor = FailingExtractor()
    with pytest.raises(RuntimeError, match="synthetic extraction failure"):
        await app.state.orchestrator.handle_message(turn.session_id, "病人本人")
    assert repository.messages[turn.session_id][-1]["content"] == "病人本人"


async def test_normal_multi_turn_exchange_and_partial_completion(client, repository) -> None:
    turn = await _create(client)
    session_id = turn["session_id"]
    answers = ["病人本人", "34歲"] + ["都沒有"] * 12 + ["今天頭暈，像周圍在轉"]
    for answer in answers:
        response = await client.post(f"/api/v1/interview-sessions/{session_id}/messages", json={"content": answer})
        assert response.status_code == 200
        turn = response.json()
    assert turn["phase"] == "SYMPTOM_COLLECTION"

    response = await client.post(f"/api/v1/interview-sessions/{session_id}/finish")
    assert response.status_code == 200
    completed = response.json()
    assert completed["phase"] == "DRAFT_READY"
    assert completed["completed"] is True
    assert "今天頭暈" in completed["draft"]["rendered_markdown"]
    assert completed["draft"]["rendered_markdown"].endswith("此為護理紀錄草稿，須由檢傷護理師確認後方可使用。\n")
    assert len(repository.messages[UUID(session_id)]) == 2 * len(answers) + 2


async def test_normal_interview_reaches_draft_without_early_finish(client) -> None:
    turn = await _create(client)
    session_id = turn["session_id"]
    answers = {
        "respondent_type": "病人本人",
        "age": "34歲",
        "chief_complaint": "今天頭暈，像周圍在轉",
        "symptom_onset": "今天早上八點開始",
        "symptom_location": "整個頭都暈",
        "symptom_quality": "周圍會轉動",
        "symptom_severity": "沒有疼痛",
        "symptom_course": "突然開始，持續存在",
        "symptom_associated": "有一點噁心",
        "symptom_trauma": "沒有跌倒或撞到",
        "symptom_function": "能自己走路和上廁所",
        "dizziness_character": "周圍在轉，也有噁心",
        "neurological_associated": "沒有新出現的麻木或無力",
        "arrival_source": "家人開車送來",
        "medical_history": "沒有慢性病",
        "medications": "沒有固定用藥",
        "allergies": "沒有已知過敏",
        "tocc_exposure": "都沒有",
        "vitals": "未量測",
    }
    turns = 0
    while not turn["completed"]:
        question_id = turn["next_question_id"]
        assert question_id is not None
        answer = "都沒有" if question_id.startswith("safety_") else answers[question_id]
        response = await client.post(
            f"/api/v1/interview-sessions/{session_id}/messages",
            json={"content": answer},
        )
        assert response.status_code == 200
        turn = response.json()
        turns += 1
        assert turns < 40

    assert turn["phase"] == "DRAFT_READY"
    assert turn["draft"]["structured"]["safety_status"] == "CLEAR"
    assert "周圍會轉動" in turn["draft"]["rendered_markdown"]
    assert "有一點噁心" in turn["draft"]["rendered_markdown"]
    assert "資料更新時間（UTC）" in turn["draft"]["rendered_markdown"]


async def test_urgent_warning_stops_questions_and_persists_draft(client, repository) -> None:
    turn = await _create(client)
    session_id = turn["session_id"]
    await client.post(f"/api/v1/interview-sessions/{session_id}/messages", json={"content": "病人本人"})
    await client.post(f"/api/v1/interview-sessions/{session_id}/messages", json={"content": "67歲"})
    response = await client.post(
        f"/api/v1/interview-sessions/{session_id}/messages",
        json={"content": "現在胸口很悶，還一直冒冷汗"},
    )
    urgent = response.json()
    assert urgent["phase"] == "ESCALATED"
    assert urgent["completed"] is True
    assert "WARN-CARDIOVASCULAR" in urgent["triggered_rule_ids"]
    assert "請立即呼叫檢傷護理師" in urgent["patient_message"]
    assert UUID(session_id) in repository.drafts


async def test_session_and_draft_retrieval(client) -> None:
    turn = await _create(client)
    session_id = turn["session_id"]
    missing = await client.get(f"/api/v1/interview-sessions/{session_id}/draft")
    assert missing.status_code == 404
    await client.post(f"/api/v1/interview-sessions/{session_id}/finish")
    session = await client.get(f"/api/v1/interview-sessions/{session_id}")
    draft = await client.get(f"/api/v1/interview-sessions/{session_id}/draft")
    assert session.status_code == 200
    assert session.json()["phase"] == "DRAFT_READY"
    assert draft.status_code == 200
    assert draft.json()["revision"] == 1


async def test_unknown_session_is_404(client) -> None:
    response = await client.get("/api/v1/interview-sessions/00000000-0000-0000-0000-000000000001")
    assert response.status_code == 404


async def test_health_and_openapi(client) -> None:
    assert (await client.get("/health/live")).json() == {"status": "ok"}
    assert (await client.get("/health/ready")).json()["status"] == "ready"
    schema = (await client.get("/openapi.json")).json()
    assert "/api/v1/interview-sessions" in schema["paths"]
