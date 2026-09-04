from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON

from ed_gateway.domain.models import utc_now

JSON_DOCUMENT = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


class InterviewSessionRow(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    phase: Mapped[str] = mapped_column(String(32), nullable=False)
    respondent_type: Mapped[str] = mapped_column(String(32), nullable=False)
    interaction_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    state: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class InterviewEventRow(Base):
    __tablename__ = "interview_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    state_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class MessageRow(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("session_id", "sequence", name="uq_messages_session_sequence"),
        Index("ix_messages_session_id", "session_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class DraftRow(Base):
    __tablename__ = "drafts"
    __table_args__ = (
        UniqueConstraint("session_id", "revision", name="uq_drafts_session_revision"),
        Index("ix_drafts_session_id", "session_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    structured: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    rendered_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
