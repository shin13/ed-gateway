# mypy: disable-error-code=no-untyped-call
from __future__ import annotations

import json
from typing import Any

import chainlit as cl
import httpx

from ed_gateway.settings import get_settings

SETTINGS = get_settings()
HTTP_TIMEOUT = 30.0


async def _api_request(method: str, path: str, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.request(method, f"{SETTINGS.API_BASE_URL}{path}", json=json_body)
            response.raise_for_status()
            value = response.json()
            if not isinstance(value, dict):
                raise ValueError("API returned an invalid response")
            return value
    except (httpx.HTTPError, ValueError):
        return {
            "patient_message": "目前無法連線到資料服務，請直接通知現場護理師。",
            "completed": True,
            "phase": "STOPPED",
            "safety_status": "PENDING",
        }


def _actions(completed: bool) -> list[cl.Action]:
    actions = [
        cl.Action(
            name="new_demo_session",
            payload={},
            label="開始新的合成展示",
            icon="refresh-cw",
        )
    ]
    if not completed:
        actions.insert(
            0,
            cl.Action(
                name="finish_interview",
                payload={},
                label="完成並產生草稿",
                icon="file-check",
            ),
        )
    return actions


async def _render_turn(turn: dict[str, Any]) -> None:
    draft = turn.get("draft")
    elements: list[cl.Text] = []
    content = str(turn.get("patient_message", ""))
    if isinstance(draft, dict):
        content = f"{content}\n\n{draft['rendered_markdown']}"
        elements.append(
            cl.Text(
                name="結構化資料 JSON",
                content=json.dumps(draft["structured"], ensure_ascii=False, indent=2),
                display="side",
                language="json",
            )
        )
    await cl.Message(
        content=content,
        actions=_actions(bool(turn.get("completed"))),
        elements=elements,
    ).send()


async def _start_session() -> None:
    turn = await _api_request(
        "POST",
        "/api/v1/interview-sessions",
        {"interaction_mode": "TEXT", "answer_language": "繁體中文"},
    )
    session_id = turn.get("session_id")
    if session_id:
        cl.user_session.set("interview_session_id", session_id)
    await _render_turn(turn)


@cl.on_chat_start
async def on_chat_start() -> None:
    await _start_session()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    session_id = cl.user_session.get("interview_session_id")
    if not session_id:
        await _start_session()
        return
    turn = await _api_request(
        "POST",
        f"/api/v1/interview-sessions/{session_id}/messages",
        {"content": message.content},
    )
    await _render_turn(turn)


@cl.action_callback("finish_interview")
async def finish_interview(action: cl.Action) -> None:
    await action.remove()
    session_id = cl.user_session.get("interview_session_id")
    if not session_id:
        await _start_session()
        return
    turn = await _api_request("POST", f"/api/v1/interview-sessions/{session_id}/finish")
    await _render_turn(turn)


@cl.action_callback("new_demo_session")
async def new_demo_session(action: cl.Action) -> None:
    await action.remove()
    await _start_session()
