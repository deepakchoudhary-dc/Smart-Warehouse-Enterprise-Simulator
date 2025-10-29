"""Pydantic schemas for scenario configuration and monitoring."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, PositiveFloat, PositiveInt

from smart_warehouse.services.scenario_engine import (
    FailureProfile,
    FleetClassConfig,
    FleetConfig,
    HorizonProfile,
    DemandProfile,
    LayoutConfig,
    OperationsProfile,
    OptimizationProfile,
    RunMetrics,
    RunStage,
    ScenarioConfig,
    ScenarioDefinition,
    ScenarioRun,
    TimelineEvent,
)

from .simulation import GridPositionSchema, LayoutSchema, SimulationStateSchema


class LayoutConfigSchema(BaseModel):
    width: PositiveInt
    height: PositiveInt
    cell_size: PositiveInt
    pickup_zones: List[GridPositionSchema]
    dropoff_zones: List[GridPositionSchema]
    obstacles: List[GridPositionSchema] = Field(default_factory=list)
    charging_zones: List[GridPositionSchema] = Field(default_factory=list)

    def to_config(self) -> LayoutConfig:
        return LayoutConfig(
            width=self.width,
            height=self.height,
            cell_size=self.cell_size,
            pickup_zones=[(pos.x, pos.y) for pos in self.pickup_zones],
            dropoff_zones=[(pos.x, pos.y) for pos in self.dropoff_zones],
            obstacles=[(pos.x, pos.y) for pos in self.obstacles],
            charging_zones=[(pos.x, pos.y) for pos in self.charging_zones],
        )

    @classmethod
    def from_config(cls, config: LayoutConfig) -> "LayoutConfigSchema":
        return cls(
            width=config.width,
            height=config.height,
            cell_size=config.cell_size,
            pickup_zones=[GridPositionSchema(x=x, y=y) for x, y in config.pickup_zones],
            dropoff_zones=[GridPositionSchema(x=x, y=y) for x, y in config.dropoff_zones],
            obstacles=[GridPositionSchema(x=x, y=y) for x, y in config.obstacles],
            charging_zones=[GridPositionSchema(x=x, y=y) for x, y in config.charging_zones],
        )


class FleetClassSchema(BaseModel):
    name: str
    speed_cells_per_tick: PositiveFloat
    payload_capacity: PositiveInt
    battery_capacity_minutes: PositiveInt

    def to_config(self) -> FleetClassConfig:
        return FleetClassConfig(
            name=self.name,
            speed_cells_per_tick=self.speed_cells_per_tick,
            payload_capacity=self.payload_capacity,
            battery_capacity_minutes=self.battery_capacity_minutes,
        )

    @classmethod
    def from_config(cls, config: FleetClassConfig) -> "FleetClassSchema":
        return cls(**config.__dict__)


class FleetConfigSchema(BaseModel):
    total_robots: PositiveInt
    classes: List[FleetClassSchema]
    starting_positions: List[GridPositionSchema] = Field(default_factory=list)

    def to_config(self) -> FleetConfig:
        return FleetConfig(
            total_robots=self.total_robots,
            classes=[cls.to_config() for cls in self.classes],
            starting_positions=[(pos.x, pos.y) for pos in self.starting_positions],
        )

    @classmethod
    def from_config(cls, config: FleetConfig) -> "FleetConfigSchema":
        return cls(
            total_robots=config.total_robots,
            classes=[FleetClassSchema.from_config(item) for item in config.classes],
            starting_positions=[GridPositionSchema(x=x, y=y) for x, y in config.starting_positions],
        )


class DemandProfileSchema(BaseModel):
    packages_per_hour: PositiveFloat
    priority_mix: dict[str, float]
    sla_minutes: dict[str, float]

    def to_config(self) -> DemandProfile:
        return DemandProfile(
            packages_per_hour=self.packages_per_hour,
            priority_mix=dict(self.priority_mix),
            sla_minutes=dict(self.sla_minutes),
        )

    @classmethod
    def from_config(cls, config: DemandProfile) -> "DemandProfileSchema":
        return cls(
            packages_per_hour=config.packages_per_hour,
            priority_mix=config.priority_mix,
            sla_minutes=config.sla_minutes,
        )


class OperationsProfileSchema(BaseModel):
    shift_minutes: PositiveInt
    cadence_ms: PositiveInt
    warmup_minutes: PositiveInt
    time_scale: PositiveFloat

    def to_config(self) -> OperationsProfile:
        return OperationsProfile(
            shift_minutes=self.shift_minutes,
            cadence_ms=self.cadence_ms,
            warmup_minutes=self.warmup_minutes,
            time_scale=self.time_scale,
        )

    @classmethod
    def from_config(cls, config: OperationsProfile) -> "OperationsProfileSchema":
        return cls(
            shift_minutes=config.shift_minutes,
            cadence_ms=config.cadence_ms,
            warmup_minutes=config.warmup_minutes,
            time_scale=config.time_scale,
        )


class FailureProfileSchema(BaseModel):
    fault_probability_per_hour: float = Field(ge=0.0)
    mean_recovery_minutes: PositiveFloat

    def to_config(self) -> FailureProfile:
        return FailureProfile(
            fault_probability_per_hour=self.fault_probability_per_hour,
            mean_recovery_minutes=self.mean_recovery_minutes,
        )

    @classmethod
    def from_config(cls, config: FailureProfile) -> "FailureProfileSchema":
        return cls(
            fault_probability_per_hour=config.fault_probability_per_hour,
            mean_recovery_minutes=config.mean_recovery_minutes,
        )


class OptimizationProfileSchema(BaseModel):
    planner: str
    assignment_policy: str
    reservation_horizon: PositiveInt

    def to_config(self) -> OptimizationProfile:
        return OptimizationProfile(
            planner=self.planner,
            assignment_policy=self.assignment_policy,
            reservation_horizon=self.reservation_horizon,
        )

    @classmethod
    def from_config(cls, config: OptimizationProfile) -> "OptimizationProfileSchema":
        return cls(
            planner=config.planner,
            assignment_policy=config.assignment_policy,
            reservation_horizon=config.reservation_horizon,
        )


class HorizonProfileSchema(BaseModel):
    duration_minutes: PositiveInt
    stop_on_completion: bool = False

    def to_config(self) -> HorizonProfile:
        return HorizonProfile(
            duration_minutes=self.duration_minutes,
            stop_on_completion=self.stop_on_completion,
        )

    @classmethod
    def from_config(cls, config: HorizonProfile) -> "HorizonProfileSchema":
        return cls(
            duration_minutes=config.duration_minutes,
            stop_on_completion=config.stop_on_completion,
        )


class ScenarioConfigSchema(BaseModel):
    name: str
    description: str
    layout: LayoutConfigSchema
    fleet: FleetConfigSchema
    demand: DemandProfileSchema
    operations: OperationsProfileSchema
    failures: FailureProfileSchema
    optimization: OptimizationProfileSchema
    horizon: HorizonProfileSchema
    metadata: dict[str, object] = Field(default_factory=dict)

    def to_config(self) -> ScenarioConfig:
        return ScenarioConfig(
            name=self.name,
            description=self.description,
            layout=self.layout.to_config(),
            fleet=self.fleet.to_config(),
            demand=self.demand.to_config(),
            operations=self.operations.to_config(),
            failures=self.failures.to_config(),
            optimization=self.optimization.to_config(),
            horizon=self.horizon.to_config(),
            metadata=dict(self.metadata),
        )

    @classmethod
    def from_definition(cls, definition: ScenarioDefinition) -> "ScenarioConfigSchema":
        cfg = definition.config
        return cls(
            name=cfg.name,
            description=cfg.description,
            layout=LayoutConfigSchema.from_config(cfg.layout),
            fleet=FleetConfigSchema.from_config(cfg.fleet),
            demand=DemandProfileSchema.from_config(cfg.demand),
            operations=OperationsProfileSchema.from_config(cfg.operations),
            failures=FailureProfileSchema.from_config(cfg.failures),
            optimization=OptimizationProfileSchema.from_config(cfg.optimization),
            horizon=HorizonProfileSchema.from_config(cfg.horizon),
            metadata=dict(cfg.metadata),
        )


class ScenarioSummarySchema(BaseModel):
    id: str
    created_at: datetime
    config: ScenarioConfigSchema

    @classmethod
    def from_definition(cls, definition: ScenarioDefinition) -> "ScenarioSummarySchema":
        return cls(id=definition.id, created_at=definition.created_at, config=ScenarioConfigSchema.from_definition(definition))


class RunMetricsSchema(BaseModel):
    throughput_per_hour: float
    sla_breaches: int
    average_cycle_time_seconds: float
    active_robots: int
    utilization: float
    fault_ratio: float
    queue_depth: int
    delivered: int
    spawned: int

    @classmethod
    def from_metrics(cls, metrics: RunMetrics) -> "RunMetricsSchema":
        return cls(**metrics.__dict__)


class TimelineEventSchema(BaseModel):
    timestamp: datetime
    type: str
    message: str
    payload: dict[str, object]

    @classmethod
    def from_event(cls, event: TimelineEvent) -> "TimelineEventSchema":
        return cls(timestamp=event.timestamp, type=event.type, message=event.message, payload=event.payload)


class ScenarioRunSchema(BaseModel):
    id: str
    scenario_id: str
    stage: RunStage
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    metrics: RunMetricsSchema
    heatmap: dict[str, int]
    error: Optional[str]

    @classmethod
    def from_run(cls, run: ScenarioRun) -> "ScenarioRunSchema":
        return cls(
            id=run.id,
            scenario_id=run.scenario_id,
            stage=run.stage,
            created_at=run.created_at,
            started_at=run.started_at,
            completed_at=run.completed_at,
            metrics=RunMetricsSchema.from_metrics(run.metrics),
            heatmap=dict(run.heatmap),
            error=run.error,
        )


class RunTickSchema(BaseModel):
    stage: RunStage
    elapsed_seconds: float
    state: SimulationStateSchema
    metrics: RunMetricsSchema
    heatmap: dict[str, int]
    recent_events: List[TimelineEventSchema]


class RunReportSchema(BaseModel):
    run: ScenarioRunSchema
    timeline: List[TimelineEventSchema]


class ScenarioRunDetailSchema(ScenarioRunSchema):
    state: Optional[SimulationStateSchema]
    timeline: List[TimelineEventSchema]
