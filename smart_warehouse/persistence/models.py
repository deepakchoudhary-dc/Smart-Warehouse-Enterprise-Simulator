"""SQLAlchemy ORM models for the warehouse simulation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from smart_warehouse.enterprise.core import PackageStatus, RobotState

from .database import Base


class PackageRecord(Base):
    __tablename__ = "packages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    status: Mapped[PackageStatus] = mapped_column(Enum(PackageStatus), default=PackageStatus.QUEUED)
    pickup_x: Mapped[int] = mapped_column(Integer, nullable=False)
    pickup_y: Mapped[int] = mapped_column(Integer, nullable=False)
    dropoff_x: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dropoff_y: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    assigned_robot: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    events: Mapped[list["EventRecord"]] = relationship(back_populates="package")


class ReservationRecord(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    robot_id: Mapped[str] = mapped_column(String(64), nullable=False)
    cell_x: Mapped[int] = mapped_column(Integer, nullable=False)
    cell_y: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    ttl_seconds: Mapped[int] = mapped_column(Integer, default=3)


class EventRecord(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    package_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("packages.id"))
    robot_id: Mapped[Optional[str]] = mapped_column(String(64))
    robot_state: Mapped[Optional[RobotState]] = mapped_column(Enum(RobotState))

    package: Mapped[Optional[PackageRecord]] = relationship(back_populates="events")
