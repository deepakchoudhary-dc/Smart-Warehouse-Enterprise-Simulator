"""Dependency providers for the API layer."""

from __future__ import annotations

from contextlib import asynccontextmanager
from functools import lru_cache
from typing import AsyncGenerator, AsyncIterator, Optional

from smart_warehouse.enterprise.config.settings import AppSettings, get_settings
from smart_warehouse.persistence import SimulationRepository, get_async_session, init_engine
from smart_warehouse.persistence.memory import InMemorySimulationRepository
from smart_warehouse.services import SimulationService
from smart_warehouse.services.scenario_engine import ScenarioEngine

__all__ = [
    "get_simulation_service",
    "reset_simulation_service",
    "get_repository",
    "get_repository_context",
    "get_app_settings",
    "reset_repository",
    "get_scenario_engine",
]


_memory_repo: Optional[InMemorySimulationRepository] = None
_scenario_engine: Optional[ScenarioEngine] = None


@lru_cache(maxsize=1)
def _get_simulation_service_singleton() -> SimulationService:
    return SimulationService()


def get_simulation_service() -> SimulationService:
    """Return the shared :class:`SimulationService` instance."""

    return _get_simulation_service_singleton()


def reset_simulation_service() -> None:
    """Reset the cached simulation service (useful for tests)."""

    _get_simulation_service_singleton.cache_clear()


def get_app_settings() -> AppSettings:
    return get_settings()


def get_scenario_engine() -> ScenarioEngine:
    global _scenario_engine
    if _scenario_engine is None:
        _scenario_engine = ScenarioEngine()
    return _scenario_engine


@asynccontextmanager
async def get_repository_context() -> AsyncIterator[SimulationRepository]:
    try:
        init_engine()
    except Exception:  # pragma: no cover - only triggered without database
        global _memory_repo
        if _memory_repo is None:
            _memory_repo = InMemorySimulationRepository()
        yield _memory_repo  # type: ignore[misc]
        return

    async with get_async_session() as session:
        yield SimulationRepository(session)


async def get_repository() -> AsyncGenerator[SimulationRepository, None]:
    try:
        init_engine()
        async with get_async_session() as session:
            yield SimulationRepository(session)
    except Exception:  # pragma: no cover - fallback path for tests
        global _memory_repo
        if _memory_repo is None:
            _memory_repo = InMemorySimulationRepository()
        yield _memory_repo


def reset_repository() -> None:
    global _memory_repo
    _memory_repo = None
