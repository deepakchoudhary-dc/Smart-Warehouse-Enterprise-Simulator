"""Manages the warehouse environment using domain models."""

from __future__ import annotations

import random
from typing import List, Optional

from smart_warehouse.enterprise.config.settings import AppSettings, get_settings
from smart_warehouse.enterprise.core import (
    GridPosition,
    Package,
    PackageStatus,
    WarehouseLayout,
    WarehouseSnapshot,
    WarehouseDimensions,
)


class WarehouseSimulator:
    """Central keeper of warehouse layout and dynamic package state."""

    def __init__(
        self,
        settings: Optional[AppSettings] = None,
        layout: Optional[WarehouseLayout] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.layout = layout or self._build_layout()
        self.packages: List[Package] = []

    def configure_layout(self, layout: WarehouseLayout) -> None:
        """Override the current static layout used by the simulator."""

        self.layout = layout
        self.packages.clear()

    def _build_layout(self) -> WarehouseLayout:
        width = self.settings.grid.width
        height = self.settings.grid.height
        cell_size = self.settings.grid.cell_size
        dimensions = WarehouseDimensions(width=width, height=height, cell_size=cell_size)

        obstacles = [GridPosition(x=10, y=y) for y in range(3, 12)]
        pickup_zones = [GridPosition(x=1, y=y) for y in (5, 7, 9)]
        dropoff_zones = [GridPosition(x=18, y=y) for y in (5, 7, 9)]

        return WarehouseLayout(
            dimensions=dimensions,
            obstacles=obstacles,
            pickup_zones=pickup_zones,
            dropoff_zones=dropoff_zones,
        )

    def spawn_package(self) -> Optional[Package]:
        """Adds a new package to a random, unoccupied pickup zone."""

        occupied_positions = {pkg.position.to_tuple() for pkg in self.packages if pkg.status != PackageStatus.DELIVERED}
        available_positions = [
            zone for zone in self.layout.pickup_zones if zone.to_tuple() not in occupied_positions
        ]
        if not available_positions:
            return None

        position = random.choice(available_positions)
        package = Package(position=position)
        self.packages.append(package)
        return package

    def get_oldest_package(self) -> Optional[Package]:
        return self.packages[0] if self.packages else None

    def nearest_dropoff(self, position: GridPosition) -> GridPosition:
        return min(
            self.layout.dropoff_zones,
            key=lambda drop: abs(drop.x - position.x) + abs(drop.y - position.y),
        )

    def complete_job(self, package_id: str) -> Optional[Package]:
        for package in list(self.packages):
            if package.id == package_id:
                package.status = PackageStatus.DELIVERED
                self.packages.remove(package)
                return package
        return None

    def snapshot(self) -> WarehouseSnapshot:
        return WarehouseSnapshot(packages=list(self.packages))
