"""API routers exposed by the server package."""

from .v1.analytics import router as analytics_router
from .v1.health import router as health_router
from .v1.observability import router as observability_router
from .v1.robots import router as robots_router
from .v1.scenarios import router as scenarios_router
from .v1.simulation import router as simulation_router

__all__ = [
	"analytics_router",
	"health_router",
	"simulation_router",
	"robots_router",
	"observability_router",
	"scenarios_router",
]
