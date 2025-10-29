"""Main entry point for the Multi-Agent Smart Warehouse Simulation."""

from __future__ import annotations

import argparse
import tkinter as tk
from typing import Dict, List

from smart_warehouse.mqtt_manager import MQTTManager
from smart_warehouse.robot_agent import RobotAgent
from smart_warehouse.enterprise.core import PackageStatus, RobotState
from smart_warehouse.services import SimulationService
from smart_warehouse.visualization.warehouse_canvas import WarehouseCanvas
from smart_warehouse.config import PACKAGE_SPAWN_RATE_S, ROBOT_COLORS, UPDATE_INTERVAL_MS


class Simulation:
    def __init__(self, master: tk.Tk, num_robots: int) -> None:
        self.master = master
        master.title("Smart Warehouse Simulation - Enhanced Visualization")

        self.service = SimulationService()
        self.robots: List[RobotAgent] = []
        self.total_jobs_completed = 0
        self.faulted_robots: set[str] = set()

        sim_frame = tk.Frame(master)
        sim_frame.pack(side=tk.LEFT, fill="both", expand=True)
        self.canvas = WarehouseCanvas(sim_frame)

        stats_frame = tk.Frame(master, padx=10, pady=10)
        stats_frame.pack(side=tk.RIGHT, fill="y")

        tk.Label(stats_frame, text="Live Statistics", font=("Arial", 14, "bold")).pack(anchor="w")

        self.stats_labels: Dict[str, tk.StringVar] = {
            "completed": tk.StringVar(value="Jobs Completed: 0"),
            "queued": tk.StringVar(value="Packages in Queue: 0"),
            "robots": tk.StringVar(value="Robot Status: 0 Active / 0 Idle"),
        }
        tk.Label(stats_frame, textvariable=self.stats_labels["completed"], font=("Arial", 12)).pack(anchor="w")
        tk.Label(stats_frame, textvariable=self.stats_labels["queued"], font=("Arial", 12)).pack(anchor="w")
        tk.Label(stats_frame, textvariable=self.stats_labels["robots"], font=("Arial", 12)).pack(anchor="w")

        layout = self.service.context.layout
        self.canvas.draw_grid_and_zones(
            obstacles=layout.obstacle_set(),
            pickup_zones=layout.pickup_tuples(),
            dropoff_zones=layout.dropoff_tuples(),
        )

        for i in range(num_robots):
            agent_id = f"AGV-{i + 1}"
            start_pos = (i, 0)
            color = ROBOT_COLORS[i % len(ROBOT_COLORS)]
            mqtt = MQTTManager(agent_id, lambda *_: None)
            mqtt.connect()
            self.robots.append(RobotAgent(agent_id, start_pos, color, mqtt))

        self.master.after(int(PACKAGE_SPAWN_RATE_S * 1000), self.spawn_package_loop)
        self.update()

    def spawn_package_loop(self) -> None:
        self.service.spawn_package()
        self.master.after(int(PACKAGE_SPAWN_RATE_S * 1000), self.spawn_package_loop)

    def _assign_jobs(self) -> None:
        telemetry = [
            robot.telemetry()
            for robot in self.robots
            if robot.state == RobotState.IDLE and robot.id not in self.faulted_robots
        ]
        assignments = self.service.assign_jobs(telemetry)

        for robot in self.robots:
            if robot.id in self.faulted_robots or robot.state != RobotState.IDLE:
                continue
            package = assignments.get(robot.id)
            if not package:
                continue
            if robot.current_job and robot.current_job.id == package.id:
                continue
            robot.assign_job(package)
            path_to_package = self.service.plan_path(robot.position, package.position)
            if path_to_package:
                robot.set_path(path_to_package)
            else:
                robot.clear_job()
                self.service.clear_assignment(robot.id)
                self.service.release_reservation(robot.id)

    def _plan_deliveries(self) -> None:
        for robot in self.robots:
            if robot.state == RobotState.DELIVERING and not robot.path:
                dropoff = self.service.dropoff_for(robot.position)
                path_to_dropoff = self.service.plan_path(robot.position, dropoff)
                if path_to_dropoff:
                    robot.set_path(path_to_dropoff)
                else:
                    robot.clear_job()
                    self.service.clear_assignment(robot.id)
                    self.service.release_reservation(robot.id)

    def update(self) -> None:
        self._assign_jobs()
        self._plan_deliveries()

        for robot in self.robots:
            delivered_id = robot.update(self.service.reservations)
            if delivered_id:
                self.service.clear_assignment(robot.id)
                self.service.complete_package(delivered_id)
                self.total_jobs_completed += 1
                self.service.release_reservation(robot.id)
            if robot.state == RobotState.IDLE:
                self.service.release_reservation(robot.id)

            health_status = self.service.observe_robot(robot.telemetry())
            if health_status.faulted:
                if robot.id not in self.faulted_robots:
                    robot.mark_faulted()
                    self.service.clear_assignment(robot.id)
                    self.service.release_reservation(robot.id)
                    self.faulted_robots.add(robot.id)
                    print(f"[{robot.id}] Marked as faulted due to inactivity.")
                continue
            if robot.id in self.faulted_robots:
                robot.recover()
                self.service.clear_fault(robot.id)
                self.faulted_robots.discard(robot.id)

        packages = self.service.simulator.packages
        self.canvas.draw_packages(packages)
        for robot in self.robots:
            self.canvas.draw_path(robot.id, robot.path)
            self.canvas.update_robot_display(robot)

        queued_count = sum(1 for pkg in packages if pkg.status != PackageStatus.DELIVERED)
        active_robots = sum(1 for robot in self.robots if robot.state != RobotState.IDLE)
        self.stats_labels["completed"].set(f"Jobs Completed: {self.total_jobs_completed}")
        self.stats_labels["queued"].set(f"Packages in Queue: {queued_count}")
        self.stats_labels["robots"].set(
            f"Robot Status: {active_robots} Active / {len(self.robots) - active_robots} Idle"
        )

        self.master.after(UPDATE_INTERVAL_MS, self.update)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Multi-Agent Warehouse Simulation.")
    parser.add_argument("--num-robots", type=int, default=3, help="Number of robots to simulate.")
    args = parser.parse_args()
    root = tk.Tk()
    app = Simulation(root, num_robots=args.num_robots)
    root.mainloop()