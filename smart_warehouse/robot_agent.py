"""Robot agent model integrated with the enterprise domain layer."""

from __future__ import annotations

from typing import List, Optional

from smart_warehouse.mqtt_manager import MQTTManager
from smart_warehouse.enterprise.core import GridPosition, Package, PackageStatus, RobotState
from smart_warehouse.enterprise.core.models import RobotTelemetry
from smart_warehouse.services.reservations import ReservationManager


class RobotAgent:
    """Automated Guided Vehicle (AGV) logic wrapper."""

    def __init__(
        self,
        agent_id: str,
        start_pos: tuple[int, int],
        color: str,
        mqtt_manager: MQTTManager,
    ) -> None:
        self.id = agent_id
        self.position = GridPosition.from_tuple(start_pos)
        self.color = color
        self.state = RobotState.IDLE
        self.mqtt = mqtt_manager

        self.path: Optional[List[GridPosition]] = None
        self.path_index: int = 0
        self.current_job: Optional[Package] = None
        self.destination: Optional[GridPosition] = None

    @property
    def x(self) -> int:
        return self.position.x

    @property
    def y(self) -> int:
        return self.position.y

    def assign_job(self, package: Package) -> None:
        if self.state != RobotState.IDLE:
            return
        self.current_job = package
        self.state = RobotState.FETCHING
        print(f"[{self.id}] Assigned job for package {self.current_job.id}")

    def set_path(self, path: List[GridPosition]) -> None:
        self.path = path
        self.path_index = 0
        self.destination = path[-1] if path else None

    def clear_job(self) -> None:
        if self.current_job:
            self.current_job.assigned_robot = None
            self.current_job.status = PackageStatus.QUEUED
        self.current_job = None
        self.path = None
        self.path_index = 0
        self.destination = None
        if self.state != RobotState.FAULTED:
            self.state = RobotState.IDLE

    def mark_faulted(self) -> Optional[str]:
        package_id = None
        if self.current_job:
            self.current_job.assigned_robot = None
            self.current_job.status = PackageStatus.QUEUED
            package_id = self.current_job.id
        self.current_job = None
        self.path = None
        self.path_index = 0
        self.destination = None
        self.state = RobotState.FAULTED
        return package_id

    def recover(self) -> None:
        if self.state == RobotState.FAULTED:
            self.state = RobotState.IDLE

    def update(self, reservations: ReservationManager) -> Optional[str]:
        delivered_package_id: Optional[str] = None
        if not self.path or self.path_index >= len(self.path):
            completed_destination = self.destination
            self.path = None
            self.destination = None
            if self.state == RobotState.FETCHING:
                reached_pickup = False
                if self.current_job:
                    reached_pickup = (
                        self.position.x == self.current_job.position.x
                        and self.position.y == self.current_job.position.y
                    )
                elif completed_destination:
                    reached_pickup = (
                        self.position.x == completed_destination.x
                        and self.position.y == completed_destination.y
                    )

                if reached_pickup:
                    self.state = RobotState.DELIVERING
                    if self.current_job:
                        self.current_job.status = PackageStatus.IN_TRANSIT
                        print(f"[{self.id}] Picked up package {self.current_job.id}.")
                    else:
                        print(f"[{self.id}] Picked up package (unknown id).")
                    return delivered_package_id
                # Await replanning if we cannot reach the pickup immediately
                return delivered_package_id

            if self.state == RobotState.DELIVERING:
                if self.current_job:
                    delivered_package_id = self.current_job.id
                    self.current_job.status = PackageStatus.DELIVERED
                    print(f"[{self.id}] Delivered package {self.current_job.id}.")
                else:
                    print(f"[{self.id}] Delivered package (unknown id).")
                self.current_job = None
                self.state = RobotState.IDLE
            return delivered_package_id

        next_pos = self.path[self.path_index]
        if reservations.is_reserved(next_pos, exclude_robot=self.id):
            print(f"[{self.id}] Waiting to move into {next_pos.to_tuple()}.")
            return None

        reservations.claim(self.id, next_pos)
        self.mqtt.publish_reservation(next_pos.x, next_pos.y)
        self.position = next_pos
        self.path_index += 1
        return None

    def telemetry(self) -> RobotTelemetry:
        return RobotTelemetry(
            robot_id=self.id,
            state=self.state,
            position=self.position,
            current_job=self.current_job.id if self.current_job else None,
            path=self.path or [],
        )
