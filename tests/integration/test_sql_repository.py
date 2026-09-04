from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import create_async_engine

from ed_gateway.application.repository import InMemoryInterviewRepository
from ed_gateway.domain.models import InteractionMode, InterviewState
from ed_gateway.infrastructure.database import create_session_factory
from ed_gateway.infrastructure.repository import SQLAlchemyInterviewRepository
from ed_gateway.infrastructure.tables import Base


async def test_sqlalchemy_repository_persists_session_across_instances(tmp_path: Path) -> None:
    database_path = tmp_path / "repository.sqlite3"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = create_session_factory(engine)
    first = SQLAlchemyInterviewRepository(factory)
    state = InterviewState(session_id=uuid4(), interaction_mode=InteractionMode.TEXT)
    await first.create_session(state, "starter")

    second = SQLAlchemyInterviewRepository(factory)
    restored = await second.get_state(state.session_id)
    assert restored is not None
    assert restored.session_id == state.session_id
    assert restored.interaction_mode == InteractionMode.TEXT
    await engine.dispose()


def test_in_memory_repository_is_a_test_double() -> None:
    assert InMemoryInterviewRepository().states == {}
