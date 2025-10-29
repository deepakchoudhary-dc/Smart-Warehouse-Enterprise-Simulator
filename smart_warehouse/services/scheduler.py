"""Task scheduling utilities for multi-agent coordination."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, Sequence

from smart_warehouse.enterprise.core import GridPosition, Package, PackageStatus, RobotState


@dataclass
class AssignmentRecord:
    robot_id: str
    package_id: str
    assigned_at: datetime = field(default_factory=datetime.utcnow)
    wait_cycles: int = 0
    last_position: Optional[GridPosition] = None


class TaskScheduler:
    """Priority-based scheduler assigning packages to idle robots."""

    def __init__(self, deadlock_threshold: int = 10) -> None:
        self._pending_assignments: dict[str, str] = {}
        self._assignment_records: Dict[str, AssignmentRecord] = {}
        self.deadlock_threshold = deadlock_threshold

    def select_job(
        self,
        robot_id: str,
        robot_position: GridPosition,
        robot_state: RobotState,
        packages: Sequence[Package],
        assignments: Optional[dict[str, str]] = None,
    ) -> Optional[Package]:
        if robot_state != RobotState.IDLE:
            return None

        assigned_packages = set(assignments.values()) if assignments else set()
        assigned_packages.update(
            pkg_id for rid, pkg_id in self._pending_assignments.items() if rid != robot_id
        )

        available_packages = [
            pkg
            for pkg in packages
            if pkg.id not in assigned_packages and pkg.status == PackageStatus.QUEUED
        ]

        if not available_packages:
            return None

        candidate = min(
            available_packages,
            key=lambda pkg: (
                self._manhattan(robot_position, pkg.position),
                pkg.created_at,
                pkg.id,
            ),
        )
        self._pending_assignments[robot_id] = candidate.id
        self._assignment_records[robot_id] = AssignmentRecord(
            robot_id=robot_id,
            package_id=candidate.id,
            last_position=robot_position,
        )
        return candidate

    @staticmethod
    def _manhattan(a: GridPosition, b: GridPosition) -> int:
        return abs(a.x - b.x) + abs(a.y - b.y)

    def clear_assignment(self, robot_id: str) -> None:
        self._pending_assignments.pop(robot_id, None)
        self._assignment_records.pop(robot_id, None)

    def pending_assignment(self, robot_id: str) -> Optional[str]:
        return self._pending_assignments.get(robot_id)

    def record_robot_state(self, robot_id: str, position: GridPosition, state: RobotState) -> None:
        record = self._assignment_records.get(robot_id)
        if not record:
            return

        if state == RobotState.IDLE:
            self.clear_assignment(robot_id)
            return

        if record.last_position and record.last_position == position:
            record.wait_cycles += 1
        else:
            record.wait_cycles = 0
        record.last_position = position

    def detect_deadlocks(self) -> list[str]:
        return [
            record.robot_id
            for record in self._assignment_records.values()
            if record.wait_cycles >= self.deadlock_threshold
        ]
