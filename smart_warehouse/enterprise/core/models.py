"""Domain models for the Smart Warehouse platform.

These models provide a typed representation of the entities that exist
within the warehouse simulation. They are intentionally framework-agnostic
so they can be reused by services, APIs, and persistence layers.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timedelta
from typing import Optional, Sequence

from pydantic import BaseModel, Field, NonNegativeInt, PositiveInt


class GridPosition(BaseModel):
    """Discrete coordinate within the warehouse grid."""

    x: NonNegativeInt = Field(..., description="X coordinate (column index).")
    y: NonNegativeInt = Field(..., description="Y coordinate (row index).")

    @classmethod
    def from_tuple(cls, position: Sequence[int]) -> "GridPosition":
        return cls(x=int(position[0]), y=int(position[1]))

    def to_tuple(self) -> tuple[int, int]:
        return (self.x, self.y)


class WarehouseDimensions(BaseModel):
    """Dimensions and cell size for the warehouse grid."""

    width: PositiveInt
    height: PositiveInt
    cell_size: PositiveInt = Field(..., description="Cell render size in pixels.")

    def contains(self, position: GridPosition) -> bool:
        """Return ``True`` if the position falls within the grid bounds."""

        return 0 <= position.x < self.width and 0 <= position.y < self.height


class ZoneType(str, enum.Enum):
    """Enumerates the supported warehouse zone categories."""

    PICKUP = "pickup"
    DROPOFF = "dropoff"
    OBSTACLE = "obstacle"
    CHARGING = "charging"


class Zone(BaseModel):
    """Named grouping of positions that share a semantic meaning."""

    name: str
    type: ZoneType
    positions: Sequence[GridPosition]

    def contains(self, position: GridPosition) -> bool:
        return any(p.x == position.x and p.y == position.y for p in self.positions)


class PackageStatus(str, enum.Enum):
    """Lifecycle states for a package within the system."""

    QUEUED = "queued"
    ASSIGNED = "assigned"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"


class Package(BaseModel):
    """Represents a unit of work to be retrieved and delivered."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    position: GridPosition
    status: PackageStatus = PackageStatus.QUEUED
    assigned_robot: Optional[str] = None


class RobotState(str, enum.Enum):
    """Operational states for a robot."""

    IDLE = "IDLE"
    FETCHING = "FETCHING"
    DELIVERING = "DELIVERING"
    FAULTED = "FAULTED"


class RobotTelemetry(BaseModel):
    """Current snapshot of a robot's key metrics."""

    robot_id: str
    state: RobotState
    position: GridPosition
    battery_level: float = Field(1.0, ge=0.0, le=1.0, description="Battery percentage (0.0-1.0)")
    current_job: Optional[str] = Field(None, description="Package ID currently assigned.")
    path: Sequence[GridPosition] = ()


class Reservation(BaseModel):
    """Temporary claim on a grid cell by a robot to avoid collisions."""

    robot_id: str
    position: GridPosition
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ttl_seconds: PositiveInt = Field(3, description="Time-to-live for the reservation in seconds.")

    @property
    def expires_at(self) -> datetime:
        return self.created_at + timedelta(seconds=self.ttl_seconds)

    def is_expired(self, reference: Optional[datetime] = None) -> bool:
        reference_time = reference or datetime.utcnow()
        return reference_time >= self.expires_at


class WarehouseSnapshot(BaseModel):
    """Immutable view of the warehouse state for consumers."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    packages: Sequence[Package]
    reservations: Sequence[Reservation] = ()
    robots: Sequence[RobotTelemetry] = ()


class WarehouseLayout(BaseModel):
    """Static layout information used by planners and renderers."""

    dimensions: WarehouseDimensions
    obstacles: Sequence[GridPosition]
    pickup_zones: Sequence[GridPosition]
    dropoff_zones: Sequence[GridPosition]
    charging_zones: Sequence[GridPosition] = ()

    def obstacle_set(self) -> set[tuple[int, int]]:
        return {pos.to_tuple() for pos in self.obstacles}

    def pickup_tuples(self) -> list[tuple[int, int]]:
        return [pos.to_tuple() for pos in self.pickup_zones]

    def dropoff_tuples(self) -> list[tuple[int, int]]:
        return [pos.to_tuple() for pos in self.dropoff_zones]

    def charging_tuples(self) -> list[tuple[int, int]]:
        return [pos.to_tuple() for pos in self.charging_zones]
