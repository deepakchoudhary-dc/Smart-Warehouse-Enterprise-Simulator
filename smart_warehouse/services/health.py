"""Robot health monitoring utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from smart_warehouse.enterprise.core import GridPosition, RobotState


@dataclass
class RobotHealthStatus:
    """Tracks stall metrics for a single robot."""

    robot_id: str
    stalled_ticks: int = 0
    faulted: bool = False
    last_position: Optional[GridPosition] = None


class RobotHealthMonitor:
    """Detects robots that remain stationary for too many update cycles."""

    def __init__(self, max_stalled_ticks: int = 20) -> None:
        self.max_stalled_ticks = max_stalled_ticks
        self._statuses: Dict[str, RobotHealthStatus] = {}

    def observe(self, robot_id: str, position: GridPosition, state: RobotState) -> RobotHealthStatus:
        status = self._statuses.get(robot_id)
        if status is None:
            status = RobotHealthStatus(robot_id=robot_id, last_position=position)
            self._statuses[robot_id] = status
            return status

        if status.last_position and position.x == status.last_position.x and position.y == status.last_position.y:
            if state not in {RobotState.IDLE, RobotState.FAULTED}:
                status.stalled_ticks += 1
        else:
            status.stalled_ticks = 0
            status.faulted = False

        status.last_position = position
        if status.stalled_ticks >= self.max_stalled_ticks:
            status.faulted = True

        return status

    def clear_fault(self, robot_id: str) -> None:
        status = self._statuses.get(robot_id)
        if status:
            status.faulted = False
            status.stalled_ticks = 0

    def status(self, robot_id: str) -> Optional[RobotHealthStatus]:
        return self._statuses.get(robot_id)

    def statuses(self) -> Dict[str, RobotHealthStatus]:
        return dict(self._statuses)
