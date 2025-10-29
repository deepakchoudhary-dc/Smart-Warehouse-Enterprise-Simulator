"""Handles all Tkinter drawing for the warehouse simulation."""

from __future__ import annotations

import tkinter as tk
from typing import Dict, Iterable, Optional, Sequence, Tuple

from smart_warehouse.config import (
    BACKGROUND_COLOR,
    CELL_SIZE,
    DROPOFF_COLOR,
    GRID_COLOR,
    GRID_HEIGHT,
    GRID_WIDTH,
    OBSTACLE_COLOR,
    PACKAGE_COLOR,
    PATH_COLOR,
    PAYLOAD_COLOR,
)
from smart_warehouse.robot_agent import RobotAgent
from smart_warehouse.enterprise.core import GridPosition, Package, RobotState


class WarehouseCanvas:
    def __init__(self, master: tk.Tk) -> None:
        self.width = GRID_WIDTH * CELL_SIZE
        self.height = GRID_HEIGHT * CELL_SIZE

        self.canvas = tk.Canvas(master, width=self.width, height=self.height, bg=BACKGROUND_COLOR)
        self.canvas.pack(pady=20, padx=20)

        self.robot_visuals: Dict[str, int] = {}
        self.robot_payloads: Dict[str, int] = {}
        self.robot_status_labels: Dict[str, int] = {}
        self.path_visuals: Dict[str, list[int]] = {}

    def draw_grid_and_zones(
        self,
        obstacles: Iterable[Tuple[int, int]],
        pickup_zones: Iterable[Tuple[int, int]],
        dropoff_zones: Iterable[Tuple[int, int]],
    ) -> None:
        self.canvas.delete("all")
        for i in range(GRID_WIDTH + 1):
            x = i * CELL_SIZE
            self.canvas.create_line(x, 0, x, self.height, fill=GRID_COLOR)
        for i in range(GRID_HEIGHT + 1):
            y = i * CELL_SIZE
            self.canvas.create_line(0, y, self.width, y, fill=GRID_COLOR)
        for x, y in pickup_zones:
            self.canvas.create_rectangle(
                x * CELL_SIZE,
                y * CELL_SIZE,
                (x + 1) * CELL_SIZE,
                (y + 1) * CELL_SIZE,
                fill=BACKGROUND_COLOR,
                outline=PACKAGE_COLOR,
                dash=(4, 4),
            )
        for x, y in dropoff_zones:
            self.canvas.create_rectangle(
                x * CELL_SIZE,
                y * CELL_SIZE,
                (x + 1) * CELL_SIZE,
                (y + 1) * CELL_SIZE,
                fill=BACKGROUND_COLOR,
                outline=DROPOFF_COLOR,
                dash=(4, 4),
            )
        for x, y in obstacles:
            self.canvas.create_rectangle(
                x * CELL_SIZE,
                y * CELL_SIZE,
                (x + 1) * CELL_SIZE,
                (y + 1) * CELL_SIZE,
                fill=OBSTACLE_COLOR,
                outline=GRID_COLOR,
            )

    def draw_packages(self, packages: Sequence[Package] | Sequence[Tuple[int, int]]) -> None:
        self.canvas.delete("package")
        for package in packages:
            if isinstance(package, Package):
                x, y = package.position.to_tuple()
            else:
                x, y = package
            self.canvas.create_rectangle(
                x * CELL_SIZE + 5,
                y * CELL_SIZE + 5,
                (x + 1) * CELL_SIZE - 5,
                (y + 1) * CELL_SIZE - 5,
                fill=PACKAGE_COLOR,
                outline="",
                tags="package",
            )

    def update_robot_display(self, robot: RobotAgent) -> None:
        agent_id = robot.id
        x, y = robot.x, robot.y
        color = robot.color
        state = robot.state
        state_label = state.value

        if agent_id in self.robot_visuals:
            self.canvas.coords(
                self.robot_visuals[agent_id],
                x * CELL_SIZE + 2,
                y * CELL_SIZE + 2,
                (x + 1) * CELL_SIZE - 2,
                (y + 1) * CELL_SIZE - 2,
            )
        else:
            self.robot_visuals[agent_id] = self.canvas.create_oval(
                x * CELL_SIZE + 2,
                y * CELL_SIZE + 2,
                (x + 1) * CELL_SIZE - 2,
                (y + 1) * CELL_SIZE - 2,
                fill=color,
                outline=color,
            )

        status_text = f"{agent_id}\n({state_label})"
        if agent_id in self.robot_status_labels:
            self.canvas.coords(
                self.robot_status_labels[agent_id],
                x * CELL_SIZE + CELL_SIZE / 2,
                y * CELL_SIZE - 10,
            )
            self.canvas.itemconfig(self.robot_status_labels[agent_id], text=status_text)
        else:
            self.robot_status_labels[agent_id] = self.canvas.create_text(
                x * CELL_SIZE + CELL_SIZE / 2,
                y * CELL_SIZE - 10,
                text=status_text,
                font=("Arial", 8),
                fill="#34495e",
            )

        if state == RobotState.DELIVERING:
            if agent_id in self.robot_payloads:
                self.canvas.coords(
                    self.robot_payloads[agent_id],
                    x * CELL_SIZE + 10,
                    y * CELL_SIZE + 10,
                    (x + 1) * CELL_SIZE - 10,
                    (y + 1) * CELL_SIZE - 10,
                )
                self.canvas.itemconfig(self.robot_payloads[agent_id], state="normal")
            else:
                self.robot_payloads[agent_id] = self.canvas.create_rectangle(
                    x * CELL_SIZE + 10,
                    y * CELL_SIZE + 10,
                    (x + 1) * CELL_SIZE - 10,
                    (y + 1) * CELL_SIZE - 10,
                    fill=PAYLOAD_COLOR,
                    outline="",
                )
        elif agent_id in self.robot_payloads:
            self.canvas.itemconfig(self.robot_payloads[agent_id], state="hidden")

    def draw_path(
        self,
        agent_id: str,
        path: Optional[Sequence[GridPosition] | Sequence[Tuple[int, int]]],
    ) -> None:
        if agent_id in self.path_visuals:
            for item in self.path_visuals[agent_id]:
                self.canvas.delete(item)
        self.path_visuals[agent_id] = []

        if not path:
            return

        for step in path:
            if isinstance(step, GridPosition):
                x, y = step.to_tuple()
            else:
                x, y = step
            center_x = x * CELL_SIZE + CELL_SIZE / 2
            center_y = y * CELL_SIZE + CELL_SIZE / 2
            visual = self.canvas.create_oval(
                center_x - 3,
                center_y - 3,
                center_x + 3,
                center_y + 3,
                fill=PATH_COLOR,
                outline="",
            )
            self.path_visuals[agent_id].append(visual)