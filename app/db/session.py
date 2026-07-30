from collections.abc import AsyncIterator

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.db.base import Base

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def init_db() -> None:
    async with get_engine().begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(ensure_lightweight_schema_updates)


def ensure_lightweight_schema_updates(connection) -> None:
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    if "documents" not in tables:
        return

    document_columns = {column["name"] for column in inspector.get_columns("documents")}
    if "source_id" not in document_columns:
        connection.exec_driver_sql("ALTER TABLE documents ADD COLUMN source_id VARCHAR(36)")


async def get_session() -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session
