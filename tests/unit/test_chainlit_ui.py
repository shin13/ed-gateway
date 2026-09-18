from ed_gateway.chainlit_ui.app import offline_notice


def test_mock_provider_warns_that_answers_are_keyword_matched() -> None:
    notice = offline_notice({"status": "ready", "database": "available", "llm": "mock"})

    assert notice is not None
    assert "離線示範模式" in notice


def test_live_provider_shows_no_notice() -> None:
    assert offline_notice({"status": "ready", "database": "available", "llm": "openai_compatible"}) is None


def test_unreadable_readiness_payload_shows_no_notice() -> None:
    assert offline_notice({}) is None
