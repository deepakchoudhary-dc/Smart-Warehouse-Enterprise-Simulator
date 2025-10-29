"""Repository helpers for storing simulation data."""

from __future__ import annotations

import json
import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from smart_warehouse.enterprise.core import Package, PackageStatus, Reservation, RobotTelemetry

from .models import EventRecord, PackageRecord, ReservationRecord


class SimulationRepository:
    """High-level persistence operations for the simulation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_package_spawn(self, package: Package) -> None:
        record = PackageRecord(
            id=uuid.UUID(package.id),
            status=package.status,
            pickup_x=package.position.x,
            pickup_y=package.position.y,
            dropoff_x=None,
            dropoff_y=None,
            assigned_robot=package.assigned_robot,
        )
        self.session.add(record)
        await self.session.flush()

    async def update_package_status(self, package: Package) -> None:
        stmt = select(PackageRecord).where(PackageRecord.id == uuid.UUID(package.id))
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            await self.record_package_spawn(package)
            return
        record.status = package.status
        record.assigned_robot = package.assigned_robot
        if package.status == PackageStatus.DELIVERED:
            record.dropoff_x = package.position.x
            record.dropoff_y = package.position.y

    async def record_reservations(self, reservations: Sequence[Reservation]) -> None:
        await self.session.execute(ReservationRecord.__table__.delete())
        for reservation in reservations:
            self.session.add(
                ReservationRecord(
                    robot_id=reservation.robot_id,
                    cell_x=reservation.position.x,
                    cell_y=reservation.position.y,
                    created_at=reservation.created_at,
                    ttl_seconds=reservation.ttl_seconds,
                )
            )

    async def record_event(
        self,
        event_type: str,
        payload: dict,
        package_id: str | None = None,
        robot: RobotTelemetry | None = None,
    ) -> None:
        record = EventRecord(
            type=event_type,
            payload=json.dumps(payload, default=str),
            package_id=uuid.UUID(package_id) if package_id else None,
            robot_id=robot.robot_id if robot else None,
            robot_state=robot.state if robot else None,
        )
        self.session.add(record)

    async def recent_events(self, limit: int = 50) -> list[EventRecord]:
        stmt = select(EventRecord).order_by(EventRecord.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def list_packages(self) -> list[PackageRecord]:
        result = await self.session.execute(select(PackageRecord))
        return list(result.scalars())
