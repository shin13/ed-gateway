from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ed_gateway.domain.models import DraftPayload, InformationSource, InterviewState, TranscriptMessage
from ed_gateway.infrastructure.tables import (
    DraftRow,
    InterviewEventRow,
    InterviewSessionRow,
    MessageRow,
)


class SQLAlchemyInterviewRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_session(self, state: InterviewState, starter_message: str) -> None:
        async with self._session_factory() as session, session.begin():
            session_row = InterviewSessionRow(
                id=state.session_id,
                phase=state.phase.value,
                respondent_type=state.respondent_type.value,
                interaction_mode=state.interaction_mode.value,
                state=state.model_dump(mode="json"),
                rule_version=state.rule_version,
                created_at=state.created_at,
                updated_at=state.updated_at,
            )
            session.add(session_row)
            # Establish the parent row before append-only records enforce their foreign keys.
            await session.flush()
            session.add(
                MessageRow(
                    session_id=state.session_id,
                    sequence=1,
                    role="assistant",
                    raw_content=starter_message,
                    source="SYSTEM",
                )
            )
            session.add(
                InterviewEventRow(
                    session_id=state.session_id,
                    event_type="SESSION_CREATED",
                    payload={"rule_version": state.rule_version},
                    state_snapshot=state.model_dump(mode="json"),
                )
            )

    async def get_state(self, session_id: UUID) -> InterviewState | None:
        async with self._session_factory() as session:
            row = await session.get(InterviewSessionRow, session_id)
            return InterviewState.model_validate(row.state) if row else None

    async def record_user_message(
        self,
        session_id: UUID,
        content: str,
        source: InformationSource,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            row = await session.get(InterviewSessionRow, session_id, with_for_update=True)
            if row is None:
                raise KeyError(str(session_id))
            current_sequence = await session.scalar(
                select(func.coalesce(func.max(MessageRow.sequence), 0)).where(MessageRow.session_id == session_id)
            )
            session.add(
                MessageRow(
                    session_id=session_id,
                    sequence=int(current_sequence or 0) + 1,
                    role="user",
                    raw_content=content,
                    source=source.value,
                )
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
        async with self._session_factory() as session, session.begin():
            row = await session.get(InterviewSessionRow, state.session_id, with_for_update=True)
            if row is None:
                raise KeyError(str(state.session_id))
            row.phase = state.phase.value
            row.respondent_type = state.respondent_type.value
            row.interaction_mode = state.interaction_mode.value
            row.state = state.model_dump(mode="json")
            row.rule_version = state.rule_version
            row.updated_at = state.updated_at

            current_sequence = await session.scalar(
                select(func.coalesce(func.max(MessageRow.sequence), 0)).where(MessageRow.session_id == state.session_id)
            )
            sequence = int(current_sequence or 0)
            if patient_message is not None:
                sequence += 1
                session.add(
                    MessageRow(
                        session_id=state.session_id,
                        sequence=sequence,
                        role="assistant",
                        raw_content=patient_message,
                        source="SYSTEM",
                    )
                )

            session.add(
                InterviewEventRow(
                    session_id=state.session_id,
                    event_type=event_type,
                    payload=event_payload,
                    state_snapshot=state.model_dump(mode="json"),
                )
            )
            if draft:
                session.add(
                    DraftRow(
                        session_id=state.session_id,
                        revision=draft.revision,
                        structured=draft.structured,
                        rendered_markdown=draft.rendered_markdown,
                        created_at=draft.created_at,
                    )
                )

    async def get_draft(self, session_id: UUID) -> DraftPayload | None:
        async with self._session_factory() as session:
            row = await session.scalar(
                select(DraftRow).where(DraftRow.session_id == session_id).order_by(DraftRow.revision.desc()).limit(1)
            )
            if row is None:
                return None
            return DraftPayload(
                revision=row.revision,
                structured=row.structured,
                rendered_markdown=row.rendered_markdown,
                created_at=row.created_at,
            )

    async def get_transcript(self, session_id: UUID) -> list[TranscriptMessage]:
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(MessageRow).where(MessageRow.session_id == session_id).order_by(MessageRow.sequence)
            )
            return [
                TranscriptMessage(
                    sequence=row.sequence,
                    role=row.role,
                    content=row.raw_content,
                    source=row.source,
                )
                for row in rows
            ]
