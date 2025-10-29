"""Legacy configuration facade backed by the enterprise settings system.

The original codebase imports this module directly (``from config import *``).
To maintain backwards compatibility while we refactor the runtime to depend
on the new :mod:`smart_warehouse.enterprise.config` package, the constants
defined here proxy values from :func:`get_settings`.
"""

from __future__ import annotations

from smart_warehouse.enterprise.config.settings import get_settings


_SETTINGS = get_settings()


# Grid dimensions
GRID_WIDTH = _SETTINGS.grid.width
GRID_HEIGHT = _SETTINGS.grid.height
CELL_SIZE = _SETTINGS.grid.cell_size  # In pixels

# Colors
GRID_COLOR = _SETTINGS.colors.grid
BACKGROUND_COLOR = _SETTINGS.colors.background
OBSTACLE_COLOR = _SETTINGS.colors.obstacle
PACKAGE_COLOR = _SETTINGS.colors.package
PATH_COLOR = _SETTINGS.colors.path
DROPOFF_COLOR = _SETTINGS.colors.dropoff
PAYLOAD_COLOR = _SETTINGS.colors.payload

# A list of colors for multiple robots
ROBOT_COLORS = list(_SETTINGS.colors.robots)

# Timing
UPDATE_INTERVAL_MS = _SETTINGS.timing.update_interval_ms
PACKAGE_SPAWN_RATE_S = _SETTINGS.timing.package_spawn_rate_s