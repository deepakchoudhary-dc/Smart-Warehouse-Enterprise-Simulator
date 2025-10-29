"""Database engine and session management."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import (  # type: ignore[attr-defined]
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from smart_warehouse.enterprise.config.settings import AppSettings, get_settings


class Base(DeclarativeBase):
    pass


metadata = Base.metadata

_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def init_engine(settings: Optional[AppSettings] = None) -> AsyncEngine:
    """Initialise (or return existing) async SQLAlchemy engine."""

    global _engine, _sessionmaker
    if _engine is not None:
        return _engine

    config = settings or get_settings()
    db = config.database
    if not db.enabled:
        raise RuntimeError("Database usage is disabled by configuration.")
    _engine = create_async_engine(
        str(db.url),
        echo=db.echo,
        pool_size=db.pool_size,
        max_overflow=db.max_overflow,
    )
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_engine() -> AsyncEngine:
    if _engine is None:
        return init_engine()
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if _sessionmaker is None:
        init_engine()
    assert _sessionmaker is not None
    return _sessionmaker


@asynccontextmanager
async def get_async_session() -> AsyncIterator[AsyncSession]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session
