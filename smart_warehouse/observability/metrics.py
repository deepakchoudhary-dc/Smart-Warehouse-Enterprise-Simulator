"""Prometheus metrics utilities."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

metrics_registry = CollectorRegistry()

REQUEST_COUNTER = Counter(
    "smart_warehouse_api_requests_total",
    "Total number of API requests handled",
    registry=metrics_registry,
)

SIMULATION_TICK_GAUGE = Gauge(
    "smart_warehouse_simulation_tick",
    "Current simulation tick",
    registry=metrics_registry,
)

PACKAGE_SPAWN_COUNTER = Counter(
    "smart_warehouse_packages_spawned_total",
    "Packages spawned into the simulation",
    registry=metrics_registry,
)

PATHFINDING_DURATION = Histogram(
    "smart_warehouse_pathfinding_seconds",
    "Duration of pathfinding computations",
    buckets=(0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
    registry=metrics_registry,
)


def record_simulation_metric(spawned: bool = False) -> None:
    """Record metrics emitted during the simulation cycle."""

    if spawned:
        PACKAGE_SPAWN_COUNTER.inc()
