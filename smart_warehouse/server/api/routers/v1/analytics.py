"""Analytics endpoints surfacing aggregated simulation insights."""

from __future__ import annotations

from collections import Counter
from typing import Dict, List

from fastapi import APIRouter, Depends

from smart_warehouse.server.api.schemas.analytics import (
    AnalyticsHeatmapSchema,
    AnalyticsRunPointSchema,
    AnalyticsScenarioSummarySchema,
)
from smart_warehouse.server.api.schemas.simulation import LayoutSchema
from smart_warehouse.server.dependencies import get_scenario_engine
from smart_warehouse.services.scenario_engine import ScenarioConfig, ScenarioEngine, ScenarioRun

router = APIRouter(prefix="/analytics", tags=["analytics"])


async def _get_engine() -> ScenarioEngine:
    return get_scenario_engine()


def _ensure_aggregate(
    aggregates: Dict[str, Dict],
    definition: ScenarioConfig,
    scenario_id: str,
    scenario_name: str,
    description: str,
) -> Dict:
    if scenario_id in aggregates:
        return aggregates[scenario_id]
    layout_domain = definition.layout.to_layout()
    aggregates[scenario_id] = {
        "scenario_name": scenario_name,
        "description": description,
        "layout": layout_domain,
        "throughput_series": [],
        "utilization_series": [],
        "heatmap": Counter(),
        "throughput_sum": 0.0,
        "utilization_sum": 0.0,
        "active_sum": 0.0,
        "fault_sum": 0.0,
        "delivered_sum": 0,
        "total_runs": 0,
        "last_run_at": None,
        "fleet_total": max(definition.fleet.total_robots, 1),
    }
    return aggregates[scenario_id]


def _aggregate_run(aggregate: Dict, run: ScenarioRun) -> None:
    metrics = run.metrics
    aggregate["total_runs"] += 1
    aggregate["throughput_sum"] += metrics.throughput_per_hour
    aggregate["utilization_sum"] += metrics.utilization
    aggregate["active_sum"] += metrics.active_robots
    aggregate["fault_sum"] += metrics.fault_ratio
    aggregate["delivered_sum"] += metrics.delivered

    timestamp = run.completed_at or run.started_at or run.created_at
    if aggregate["last_run_at"] is None or (
        timestamp and aggregate["last_run_at"] and timestamp > aggregate["last_run_at"]
    ):
        aggregate["last_run_at"] = timestamp

    total_robots = aggregate["fleet_total"]
    idle = max(total_robots - metrics.active_robots, 0)
    point = {
        "run_id": run.id,
        "scenario_id": run.scenario_id,
        "scenario_name": aggregate["scenario_name"],
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "throughput_per_hour": metrics.throughput_per_hour,
        "delivered": metrics.delivered,
        "sla_breaches": metrics.sla_breaches,
        "utilization": metrics.utilization,
        "active_robots": metrics.active_robots,
        "idle_robots": idle,
        "fault_ratio": metrics.fault_ratio,
    }
    aggregate["throughput_series"].append(point)
    aggregate["utilization_series"].append(point)

    heatmap: Counter = aggregate["heatmap"]
    for cell, count in run.heatmap.items():
        heatmap[cell] += int(count)


@router.get("/scenarios", response_model=List[AnalyticsScenarioSummarySchema])
async def analytics_by_scenario(
    engine: ScenarioEngine = Depends(_get_engine),
) -> List[AnalyticsScenarioSummarySchema]:
    runs = await engine.list_runs()
    definitions = await engine.list_scenarios()
    definition_lookup: Dict[str, ScenarioConfig] = {item.id: item.config for item in definitions}

    aggregates: Dict[str, Dict] = {}

    for run in runs:
        config = definition_lookup.get(run.scenario_id)
        if config is None:
            scenario = await engine.get_scenario(run.scenario_id)
            config = scenario.config
            definition_lookup[scenario.id] = config
        aggregate = _ensure_aggregate(
            aggregates,
            config,
            run.scenario_id,
            config.name,
            config.description,
        )
    _aggregate_run(aggregate, run)

    # ensure scenarios with zero runs are still returned
    for scenario_id, config in definition_lookup.items():
        _ensure_aggregate(aggregates, config, scenario_id, config.name, config.description)

    summaries: List[AnalyticsScenarioSummarySchema] = []
    for scenario_id, aggregate in sorted(aggregates.items(), key=lambda item: item[1]["scenario_name"].lower()):
        total_runs: int = aggregate["total_runs"]
        throughput_series = [AnalyticsRunPointSchema(**point) for point in aggregate["throughput_series"]]
        utilization_series = [AnalyticsRunPointSchema(**point) for point in aggregate["utilization_series"]]
        heatmap_counter: Counter = aggregate["heatmap"]
        heatmap_schema = AnalyticsHeatmapSchema(
            total_visits=int(sum(heatmap_counter.values())),
            max_visits=int(max(heatmap_counter.values()) if heatmap_counter else 0),
            cells=dict(sorted(heatmap_counter.items())),
        )
        layout_schema = LayoutSchema.from_domain(aggregate["layout"])
        summaries.append(
            AnalyticsScenarioSummarySchema(
                scenario_id=scenario_id,
                scenario_name=aggregate["scenario_name"],
                description=aggregate["description"],
                fleet_total_robots=aggregate["fleet_total"],
                total_runs=total_runs,
                avg_throughput_per_hour=aggregate["throughput_sum"] / total_runs if total_runs else 0.0,
                avg_utilization=aggregate["utilization_sum"] / total_runs if total_runs else 0.0,
                avg_active_robots=aggregate["active_sum"] / total_runs if total_runs else 0.0,
                total_delivered=aggregate["delivered_sum"],
                avg_fault_ratio=aggregate["fault_sum"] / total_runs if total_runs else 0.0,
                throughput_series=throughput_series,
                utilization_series=utilization_series,
                heatmap=heatmap_schema,
                layout=layout_schema,
                last_run_at=aggregate["last_run_at"],
            )
        )

    return summaries


__all__ = ["router"]
