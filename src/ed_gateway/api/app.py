from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from fastapi import FastAPI, HTTPException, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from ed_gateway.application.exports import render_session_export
from ed_gateway.application.repository import InterviewRepository
from ed_gateway.bootstrap import create_orchestrator
from ed_gateway.domain.models import (
    CreateSessionRequest,
    DraftPayload,
    MessageRequest,
    SessionExport,
    SessionView,
    TurnResponse,
)
from ed_gateway.infrastructure.database import create_engine, create_session_factory
from ed_gateway.infrastructure.repository import SQLAlchemyInterviewRepository
from ed_gateway.infrastructure.tables import Base
from ed_gateway.settings import Settings, get_settings


def create_app(*, settings: Settings | None = None, repository: InterviewRepository | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    engine: AsyncEngine | None = None
    if repository is None:
        engine = create_engine(resolved_settings.database_url)
        repository = SQLAlchemyInterviewRepository(create_session_factory(engine))
    orchestrator = create_orchestrator(repository=repository, settings=resolved_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if engine is not None and resolved_settings.APP_ENV == "test":
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
        yield
        if engine is not None:
            await engine.dispose()

    app = FastAPI(
        title=resolved_settings.APP_NAME,
        version="0.1.0",
        description=(
            "Research demonstration API for structured ED intake and nurse-review drafts. "
            "It does not diagnose or assign formal triage levels."
        ),
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.engine = engine
    app.state.repository = repository
    app.state.orchestrator = orchestrator

    @app.get("/health/live", tags=["health"])
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    async def ready(response: Response) -> dict[str, Any]:
        if engine is None:
            return {"status": "ready", "database": "in-memory", "llm": resolved_settings.LLM_PROVIDER}
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "not_ready", "database": "unavailable", "llm": resolved_settings.LLM_PROVIDER}
        return {"status": "ready", "database": "available", "llm": resolved_settings.LLM_PROVIDER}

    @app.post("/api/v1/interview-sessions", response_model=TurnResponse, status_code=201)
    async def create_session(request: CreateSessionRequest) -> TurnResponse:
        return await orchestrator.create_session(request)

    @app.post("/api/v1/interview-sessions/{session_id}/messages", response_model=TurnResponse)
    async def add_message(session_id: UUID, request: MessageRequest) -> TurnResponse:
        try:
            return await orchestrator.handle_message(session_id, request.content)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Interview session not found") from exc

    @app.post("/api/v1/interview-sessions/{session_id}/finish", response_model=TurnResponse)
    async def finish(session_id: UUID) -> TurnResponse:
        try:
            return await orchestrator.finish(session_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Interview session not found") from exc

    @app.get("/api/v1/interview-sessions/{session_id}", response_model=SessionView)
    async def get_session(session_id: UUID) -> SessionView:
        try:
            state = await orchestrator.get_state(session_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Interview session not found") from exc
        return SessionView(
            session_id=state.session_id,
            phase=state.phase,
            respondent_type=state.respondent_type,
            interaction_mode=state.interaction_mode,
            state=state,
            created_at=state.created_at,
            updated_at=state.updated_at,
        )

    @app.get("/api/v1/interview-sessions/{session_id}/draft", response_model=DraftPayload)
    async def get_draft(session_id: UUID) -> DraftPayload:
        try:
            draft = await orchestrator.get_draft(session_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Interview session not found") from exc
        if draft is None:
            raise HTTPException(status_code=404, detail="Draft is not ready")
        return draft

    @app.get("/api/v1/interview-sessions/{session_id}/export", response_model=SessionExport)
    async def export_session(session_id: UUID) -> SessionExport:
        try:
            state = await orchestrator.get_state(session_id)
            transcript = await orchestrator.get_transcript(session_id)
            draft = await orchestrator.get_draft(session_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Interview session not found") from exc
        return SessionExport(
            session_id=session_id,
            rendered_markdown=render_session_export(
                state=state,
                transcript=transcript,
                draft=draft,
                llm_provider=resolved_settings.LLM_PROVIDER,
                llm_model=resolved_settings.LLM_MODEL,
            ),
        )

    return app


app = create_app()
