"""In-memory repository used when persistent storage is unavailable."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Sequence

from smart_warehouse.enterprise.core import Package, Reservation, RobotTelemetry
from smart_warehouse.enterprise.core.models import PackageStatus


@dataclass
class InMemoryEvent:
    id: int
    created_at: datetime
    type: str
    payload: str
    package_id: str | None = None
    robot_id: str | None = None
    robot_state: str | None = None


@dataclass
class InMemoryPackage:
    package: Package


class InMemorySimulationRepository:
    """Simplistic repository that keeps entities in process memory."""

    def __init__(self) -> None:
        self.events: List[InMemoryEvent] = []
        self.packages: dict[str, InMemoryPackage] = {}

    @property
    def session(self):  # pragma: no cover - compatibility shim
        class _Session:
            async def commit(self_inner) -> None:
                return None

        return _Session()

    async def record_package_spawn(self, package: Package) -> None:
        self.packages[package.id] = InMemoryPackage(package)

    async def update_package_status(self, package: Package) -> None:
        self.packages[package.id] = InMemoryPackage(package)

    async def record_reservations(self, reservations: Sequence[Reservation]) -> None:  # pragma: no cover - noop
        return None

    async def record_event(
        self,
        event_type: str,
        payload: dict,
        package_id: str | None = None,
        robot: RobotTelemetry | None = None,
    ) -> None:
        self.events.append(
            InMemoryEvent(
                id=len(self.events) + 1,
                created_at=datetime.utcnow(),
                type=event_type,
                payload=json.dumps(payload),
                package_id=package_id,
                robot_id=robot.robot_id if robot else None,
                robot_state=robot.state.value if robot else None,
            )
        )

    async def recent_events(self, limit: int = 50) -> List[InMemoryEvent]:
        return list(reversed(self.events))[:limit]

    async def list_packages(self) -> List[InMemoryPackage]:  # pragma: no cover - compatibility shim
        return list(self.packages.values())
