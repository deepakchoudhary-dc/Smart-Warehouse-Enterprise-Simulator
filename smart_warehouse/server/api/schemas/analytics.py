"""Pydantic schemas powering analytics endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel

from smart_warehouse.server.api.schemas.simulation import LayoutSchema


class AnalyticsHeatmapSchema(BaseModel):
    total_visits: int
    max_visits: int
    cells: Dict[str, int]


class AnalyticsRunPointSchema(BaseModel):
    run_id: str
    scenario_id: str
    scenario_name: str
    started_at: datetime | None
    completed_at: datetime | None
    throughput_per_hour: float
    delivered: int
    sla_breaches: int
    utilization: float
    active_robots: int
    idle_robots: int
    fault_ratio: float


class AnalyticsScenarioSummarySchema(BaseModel):
    scenario_id: str
    scenario_name: str
    description: str
    fleet_total_robots: int
    total_runs: int
    avg_throughput_per_hour: float
    avg_utilization: float
    avg_active_robots: float
    total_delivered: int
    avg_fault_ratio: float
    throughput_series: List[AnalyticsRunPointSchema]
    utilization_series: List[AnalyticsRunPointSchema]
    heatmap: AnalyticsHeatmapSchema
    layout: LayoutSchema
    last_run_at: datetime | None


__all__ = [
    "AnalyticsScenarioSummarySchema",
    "AnalyticsRunPointSchema",
    "AnalyticsHeatmapSchema",
]
