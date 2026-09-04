import os

import httpx
import pytest

BASE_URL = os.environ.get("ED_GATEWAY_BASE_URL")


@pytest.mark.smoke
@pytest.mark.skipif(not BASE_URL, reason="ED_GATEWAY_BASE_URL is not configured")
def test_running_stack_normal_and_escalation_paths() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=10) as client:
        assert client.get("/health/ready").json()["status"] == "ready"

        normal = client.post("/api/v1/interview-sessions", json={}).json()
        normal_id = normal["session_id"]
        for answer in ["病人本人", "29歲"] + ["都沒有"] * 12 + ["今天頭暈"]:
            normal = client.post(f"/api/v1/interview-sessions/{normal_id}/messages", json={"content": answer}).json()
        normal = client.post(f"/api/v1/interview-sessions/{normal_id}/finish").json()
        assert normal["phase"] == "DRAFT_READY"
        assert "今天頭暈" in normal["draft"]["rendered_markdown"]

        urgent = client.post("/api/v1/interview-sessions", json={}).json()
        urgent_id = urgent["session_id"]
        for answer in ["病人本人", "64歲", "胸痛還冒冷汗"]:
            urgent = client.post(f"/api/v1/interview-sessions/{urgent_id}/messages", json={"content": answer}).json()
        assert urgent["phase"] == "ESCALATED"
        assert urgent["triggered_rule_ids"] == ["WARN-CARDIOVASCULAR"]

        persisted = client.get(f"/api/v1/interview-sessions/{normal_id}").json()
        draft = client.get(f"/api/v1/interview-sessions/{normal_id}/draft").json()
        assert persisted["phase"] == "DRAFT_READY"
        assert draft["revision"] == 1
