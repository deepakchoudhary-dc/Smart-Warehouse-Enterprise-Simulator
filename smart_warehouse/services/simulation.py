"""High-level orchestration of the warehouse simulation domain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from smart_warehouse.enterprise.config.settings import AppSettings, get_settings
from smart_warehouse.enterprise.core import (
    GridPosition,
    Package,
    PackageStatus,
    Reservation,
    RobotState,
    WarehouseLayout,
    WarehouseSnapshot,
)
from smart_warehouse.enterprise.core.models import RobotTelemetry
from smart_warehouse.pathfinding import build_reservation_table, find_path_astar, find_path_bfs
from smart_warehouse.services.health import RobotHealthMonitor, RobotHealthStatus
from smart_warehouse.services.reservations import ReservationManager
from smart_warehouse.services.scheduler import TaskScheduler
from smart_warehouse.warehouse_simulator import WarehouseSimulator


@dataclass
class SimulationContext:
    settings: AppSettings
    layout: WarehouseLayout


class SimulationService:
    """Coordinates the core simulation loop independent of any UI."""

    def __init__(
        self,
        simulator: Optional[WarehouseSimulator] = None,
        scheduler: Optional[TaskScheduler] = None,
        reservations: Optional[ReservationManager] = None,
        settings: Optional[AppSettings] = None,
        health_monitor: Optional[RobotHealthMonitor] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.simulator = simulator or WarehouseSimulator(self.settings)
        self.scheduler = scheduler or TaskScheduler()
        self.reservations = reservations or ReservationManager()
        self.health_monitor = health_monitor or RobotHealthMonitor()

    @property
    def context(self) -> SimulationContext:
        return SimulationContext(settings=self.settings, layout=self.simulator.layout)

    def spawn_package(self) -> Optional[Package]:
        return self.simulator.spawn_package()

    def assign_jobs(self, telemetry: Iterable[RobotTelemetry]) -> Dict[str, Package]:
        packages = self.simulator.packages
        assignments: Dict[str, Package] = {}

        snapshot_telemetry = list(telemetry)
        for robot in snapshot_telemetry:
            self.scheduler.record_robot_state(robot.robot_id, robot.position, robot.state)

        for robot in snapshot_telemetry:
            if robot.state != RobotState.IDLE:
                continue
            package = self.scheduler.select_job(
                robot_id=robot.robot_id,
                robot_position=robot.position,
                robot_state=robot.state,
                packages=packages,
                assignments={rid: pkg.id for rid, pkg in assignments.items()},
            )
            if package:
                package.assigned_robot = robot.robot_id
                package.status = PackageStatus.ASSIGNED
                assignments[robot.robot_id] = package
            else:
                self.scheduler.clear_assignment(robot.robot_id)

        for robot_id in self.scheduler.detect_deadlocks():
            package_id = self.scheduler.pending_assignment(robot_id)
            if not package_id:
                continue
            for package in packages:
                if package.id == package_id:
                    package.status = PackageStatus.QUEUED
                    package.assigned_robot = None
                    break
            self.scheduler.clear_assignment(robot_id)
            self.reservations.release(robot_id)

        return assignments

    def plan_path(
        self,
        start: GridPosition,
        end: GridPosition,
        reserved_paths: Optional[Dict[str, List[GridPosition]]] = None,
    ) -> List[GridPosition]:
        layout = self.simulator.layout
        obstacles = layout.obstacle_set()

        reservation_table = {}
        if reserved_paths:
            reservation_table = build_reservation_table(
                {rid: [pos.to_tuple() for pos in path] for rid, path in reserved_paths.items()}
            )

        active_reservations = self.reservations.reservations()
        if active_reservations:
            reservation_table.setdefault(1, set()).update(
                {(res.position.x, res.position.y) for res in active_reservations}
            )

        path = find_path_astar(
            start=start.to_tuple(),
            end=end.to_tuple(),
            obstacles=obstacles,
            grid_width=layout.dimensions.width,
            grid_height=layout.dimensions.height,
            reservations=reservation_table or None,
        )
        if not path:
            fallback = find_path_bfs(
                start=start.to_tuple(),
                end=end.to_tuple(),
                obstacles=obstacles,
                grid_width=layout.dimensions.width,
                grid_height=layout.dimensions.height,
                forbidden={(res.position.x, res.position.y) for res in active_reservations},
            )
            if not fallback:
                return []
            path = fallback
        grid_positions = [GridPosition.from_tuple(coords) for coords in path]
        if grid_positions and grid_positions[0] == start:
            grid_positions = grid_positions[1:]
        return grid_positions

    def reserve_next_cell(self, robot_id: str, position: GridPosition) -> Reservation:
        return self.reservations.claim(robot_id, position)

    def release_reservation(self, robot_id: str) -> None:
        self.reservations.release(robot_id)

    def snapshot(self, telemetry: Iterable[RobotTelemetry]) -> WarehouseSnapshot:
        return WarehouseSnapshot(
            packages=list(self.simulator.packages),
            reservations=self.reservations.reservations(),
            robots=list(telemetry),
        )

    def complete_package(self, package_id: str) -> Optional[Package]:
        return self.simulator.complete_job(package_id)

    def dropoff_for(self, position: GridPosition) -> GridPosition:
        return self.simulator.nearest_dropoff(position)

    def observe_robot(self, telemetry: RobotTelemetry) -> RobotHealthStatus:
        return self.health_monitor.observe(telemetry.robot_id, telemetry.position, telemetry.state)

    def clear_assignment(self, robot_id: str) -> None:
        self.scheduler.clear_assignment(robot_id)

    def clear_fault(self, robot_id: str) -> None:
        self.health_monitor.clear_fault(robot_id)

    def reset(self) -> None:
        self.simulator.packages.clear()
        self.reservations.reset()
        self.scheduler = TaskScheduler()
        self.health_monitor = RobotHealthMonitor()