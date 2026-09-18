from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from ed_gateway.domain.models import DraftPayload, InformationSource, InterviewState, TranscriptMessage


class InterviewRepository(Protocol):
    async def create_session(self, state: InterviewState, starter_message: str) -> None: ...

    async def get_state(self, session_id: UUID) -> InterviewState | None: ...

    async def record_user_message(
        self,
        session_id: UUID,
        content: str,
        source: InformationSource,
    ) -> None: ...

    async def save_turn(
        self,
        *,
        state: InterviewState,
        patient_message: str | None,
        event_type: str,
        event_payload: dict[str, Any],
        draft: DraftPayload | None = None,
    ) -> None: ...

    async def get_draft(self, session_id: UUID) -> DraftPayload | None: ...

    async def get_transcript(self, session_id: UUID) -> list[TranscriptMessage]: ...


class InMemoryInterviewRepository:
    def __init__(self) -> None:
        self.states: dict[UUID, InterviewState] = {}
        self.messages: dict[UUID, list[dict[str, Any]]] = {}
        self.events: dict[UUID, list[dict[str, Any]]] = {}
        self.drafts: dict[UUID, DraftPayload] = {}

    async def create_session(self, state: InterviewState, starter_message: str) -> None:
        self.states[state.session_id] = state.model_copy(deep=True)
        self.messages[state.session_id] = [
            {"sequence": 1, "role": "assistant", "content": starter_message, "source": "SYSTEM"}
        ]
        self.events[state.session_id] = [{"event_type": "SESSION_CREATED", "state": state.model_dump(mode="json")}]

    async def get_state(self, session_id: UUID) -> InterviewState | None:
        state = self.states.get(session_id)
        return state.model_copy(deep=True) if state else None

    async def record_user_message(
        self,
        session_id: UUID,
        content: str,
        source: InformationSource,
    ) -> None:
        messages = self.messages.setdefault(session_id, [])
        messages.append(
            {
                "sequence": len(messages) + 1,
                "role": "user",
                "content": content,
                "source": source.value,
            }
        )

    async def save_turn(
        self,
        *,
        state: InterviewState,
        patient_message: str | None,
        event_type: str,
        event_payload: dict[str, Any],
        draft: DraftPayload | None = None,
    ) -> None:
        self.states[state.session_id] = state.model_copy(deep=True)
        messages = self.messages.setdefault(state.session_id, [])
        if patient_message is not None:
            messages.append(
                {
                    "sequence": len(messages) + 1,
                    "role": "assistant",
                    "content": patient_message,
                    "source": "SYSTEM",
                }
            )
        self.events.setdefault(state.session_id, []).append(
            {"event_type": event_type, "payload": event_payload, "state": state.model_dump(mode="json")}
        )
        if draft:
            self.drafts[state.session_id] = draft.model_copy(deep=True)

    async def get_draft(self, session_id: UUID) -> DraftPayload | None:
        draft = self.drafts.get(session_id)
        return draft.model_copy(deep=True) if draft else None

    async def get_transcript(self, session_id: UUID) -> list[TranscriptMessage]:
        return [TranscriptMessage(**message) for message in self.messages.get(session_id, [])]
