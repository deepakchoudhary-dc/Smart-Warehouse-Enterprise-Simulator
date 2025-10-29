"""Pydantic schemas for simulation API responses."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Iterable, List, Optional

from pydantic import BaseModel, Field

from smart_warehouse.enterprise.config.settings import AppSettings
from smart_warehouse.enterprise.core import Package, Reservation, WarehouseLayout, WarehouseSnapshot
from smart_warehouse.enterprise.core.models import RobotTelemetry
from smart_warehouse.services.health import RobotHealthStatus
from smart_warehouse.persistence.models import EventRecord


class GridPositionSchema(BaseModel):
    x: int
    y: int

    @classmethod
    def from_tuple(cls, position: tuple[int, int]) -> "GridPositionSchema":
        return cls(x=position[0], y=position[1])


class ReservationSchema(BaseModel):
    robot_id: str
    position: GridPositionSchema
    expires_at: datetime

    @classmethod
    def from_domain(cls, reservation: Reservation) -> "ReservationSchema":
        return cls(
            robot_id=reservation.robot_id,
            position=GridPositionSchema(x=reservation.position.x, y=reservation.position.y),
            expires_at=reservation.expires_at,
        )


class PackageSchema(BaseModel):
    id: str
    position: GridPositionSchema
    status: str
    assigned_robot: Optional[str]
    created_at: datetime

    @classmethod
    def from_domain(cls, package: Package) -> "PackageSchema":
        return cls(
            id=package.id,
            position=GridPositionSchema(x=package.position.x, y=package.position.y),
            status=package.status.value,
            assigned_robot=package.assigned_robot,
            created_at=package.created_at,
        )


class RobotTelemetrySchema(BaseModel):
    robot_id: str
    state: str
    position: GridPositionSchema
    battery_level: float
    current_job: Optional[str]
    path: List[GridPositionSchema]

    @classmethod
    def from_domain(cls, telemetry: RobotTelemetry) -> "RobotTelemetrySchema":
        return cls(
            robot_id=telemetry.robot_id,
            state=telemetry.state.value,
            position=GridPositionSchema(x=telemetry.position.x, y=telemetry.position.y),
            battery_level=telemetry.battery_level,
            current_job=telemetry.current_job,
            path=[GridPositionSchema(x=pos.x, y=pos.y) for pos in telemetry.path],
        )


class LayoutSchema(BaseModel):
    width: int
    height: int
    cell_size: int
    obstacles: List[GridPositionSchema]
    pickup_zones: List[GridPositionSchema]
    dropoff_zones: List[GridPositionSchema]
    charging_zones: List[GridPositionSchema] = Field(default_factory=list)

    @classmethod
    def from_domain(cls, layout: WarehouseLayout) -> "LayoutSchema":
        return cls(
            width=layout.dimensions.width,
            height=layout.dimensions.height,
            cell_size=layout.dimensions.cell_size,
            obstacles=[GridPositionSchema(x=pos.x, y=pos.y) for pos in layout.obstacles],
            pickup_zones=[GridPositionSchema(x=pos.x, y=pos.y) for pos in layout.pickup_zones],
            dropoff_zones=[GridPositionSchema(x=pos.x, y=pos.y) for pos in layout.dropoff_zones],
            charging_zones=[GridPositionSchema(x=pos.x, y=pos.y) for pos in layout.charging_zones],
        )


class SimulationStateSchema(BaseModel):
    packages: List[PackageSchema]
    reservations: List[ReservationSchema]
    robots: List[RobotTelemetrySchema]
    layout: LayoutSchema

    @classmethod
    def from_domain(
        cls,
        snapshot: WarehouseSnapshot,
        layout: WarehouseLayout,
        telemetry: Optional[Iterable[RobotTelemetry]] = None,
    ) -> "SimulationStateSchema":
        robot_data = telemetry or snapshot.robots
        return cls(
            packages=[PackageSchema.from_domain(pkg) for pkg in snapshot.packages],
            reservations=[ReservationSchema.from_domain(res) for res in snapshot.reservations],
            robots=[RobotTelemetrySchema.from_domain(robot) for robot in robot_data],
            layout=LayoutSchema.from_domain(layout),
        )


class EventSchema(BaseModel):
    id: int
    created_at: datetime
    type: str
    payload: dict
    package_id: Optional[str]
    robot_id: Optional[str]
    robot_state: Optional[str]

    @classmethod
    def from_record(cls, record: EventRecord | Any) -> "EventSchema":  # type: ignore[name-defined]
        payload_raw = getattr(record, "payload", None)
        payload = json.loads(payload_raw) if isinstance(payload_raw, str) and payload_raw else payload_raw or {}
        robot_state = getattr(record, "robot_state", None)
        if hasattr(robot_state, "value"):
            robot_state = robot_state.value
        return cls(
            id=record.id,
            created_at=record.created_at,
            type=record.type,
            payload=payload,
            package_id=str(record.package_id) if record.package_id else None,
            robot_id=record.robot_id,
            robot_state=robot_state,
        )


class AppConfigSchema(BaseModel):
    environment: str
    mqtt: dict
    database: dict
    telemetry: dict

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "AppConfigSchema":
        return cls(
            environment=settings.environment,
            mqtt=settings.mqtt.model_dump(exclude_none=True),
            database=settings.database.model_dump(),
            telemetry=settings.telemetry.model_dump(),
        )


class RobotHealthSchema(BaseModel):
    robot_id: str
    stalled_ticks: int
    faulted: bool

    @classmethod
    def from_status(cls, status: RobotHealthStatus) -> "RobotHealthSchema":
        return cls(
            robot_id=status.robot_id,
            stalled_ticks=status.stalled_ticks,
            faulted=status.faulted,
        )