"""Scenario orchestration layer for enterprise-grade simulations."""

from __future__ import annotations

import asyncio
import random
import uuid
from collections import Counter, defaultdict
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional

UPDATE_INTERVAL_SECONDS = 5.0

from smart_warehouse.enterprise.core import (
    GridPosition,
    Package,
    PackageStatus,
    RobotState,
    WarehouseDimensions,
    WarehouseLayout,
    WarehouseSnapshot,
)
from smart_warehouse.robot_agent import RobotAgent
from smart_warehouse.services import SimulationService
from smart_warehouse.services.reservations import ReservationManager
from smart_warehouse.warehouse_simulator import WarehouseSimulator


class RunStage(str, Enum):
    """Lifecycle stages for a scenario run."""

    QUEUED = "QUEUED"
    WARMING_UP = "WARMING_UP"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class LayoutConfig:
    width: int
    height: int
    cell_size: int
    pickup_zones: List[tuple[int, int]]
    dropoff_zones: List[tuple[int, int]]
    obstacles: List[tuple[int, int]] = field(default_factory=list)
    charging_zones: List[tuple[int, int]] = field(default_factory=list)

    def to_layout(self) -> WarehouseLayout:
        return WarehouseLayout(
            dimensions=WarehouseDimensions(width=self.width, height=self.height, cell_size=self.cell_size),
            obstacles=[GridPosition(x=o[0], y=o[1]) for o in self.obstacles],
            pickup_zones=[GridPosition(x=p[0], y=p[1]) for p in self.pickup_zones],
            dropoff_zones=[GridPosition(x=d[0], y=d[1]) for d in self.dropoff_zones],
            charging_zones=[GridPosition(x=c[0], y=c[1]) for c in self.charging_zones],
        )


@dataclass
class FleetClassConfig:
    name: str
    speed_cells_per_tick: float
    payload_capacity: int
    battery_capacity_minutes: int


@dataclass
class FleetConfig:
    total_robots: int
    classes: List[FleetClassConfig] = field(default_factory=list)
    starting_positions: List[tuple[int, int]] = field(default_factory=list)


@dataclass
class DemandProfile:
    packages_per_hour: float
    priority_mix: Dict[str, float] = field(default_factory=lambda: {"standard": 0.7, "express": 0.3})
    sla_minutes: Dict[str, float] = field(default_factory=lambda: {"standard": 30.0, "express": 12.0})


@dataclass
class OperationsProfile:
    shift_minutes: int
    cadence_ms: int = 500
    warmup_minutes: int = 2
    time_scale: float = 10.0


@dataclass
class FailureProfile:
    fault_probability_per_hour: float = 0.1
    mean_recovery_minutes: float = 5.0


@dataclass
class OptimizationProfile:
    planner: str = "astar"
    assignment_policy: str = "hungarian"
    reservation_horizon: int = 6


@dataclass
class HorizonProfile:
    duration_minutes: int
    stop_on_completion: bool = False


@dataclass
class ScenarioConfig:
    """Full configuration for a scenario."""

    name: str
    description: str
    layout: LayoutConfig
    fleet: FleetConfig
    demand: DemandProfile
    operations: OperationsProfile
    failures: FailureProfile
    optimization: OptimizationProfile
    horizon: HorizonProfile
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScenarioDefinition:
    id: str
    created_at: datetime
    config: ScenarioConfig


@dataclass
class RunMetrics:
    throughput_per_hour: float = 0.0
    sla_breaches: int = 0
    average_cycle_time_seconds: float = 0.0
    active_robots: int = 0
    utilization: float = 0.0
    fault_ratio: float = 0.0
    queue_depth: int = 0
    delivered: int = 0
    spawned: int = 0


@dataclass
class TimelineEvent:
    timestamp: datetime
    type: str
    message: str
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RunTick:
    stage: RunStage
    elapsed_seconds: float
    state: WarehouseSnapshot
    metrics: RunMetrics
    heatmap: Dict[str, int]
    recent_events: List[TimelineEvent]


@dataclass
class ScenarioRun:
    id: str
    scenario_id: str
    stage: RunStage
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metrics: RunMetrics = field(default_factory=RunMetrics)
    timeline: List[TimelineEvent] = field(default_factory=list)
    last_snapshot: Optional[WarehouseSnapshot] = None
    heatmap: Dict[str, int] = field(default_factory=dict)
    error: Optional[str] = None


class _NoOpMQTT:
    """Local stub for RobotAgent MQTT interactions during scenario runs."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id

    def connect(self) -> None:  # pragma: no cover - no side effects needed
        return

    def publish_reservation(self, *_: Any) -> None:  # pragma: no cover - noop
        return

    def disconnect(self) -> None:  # pragma: no cover - noop
        return


class ScenarioRunner:
    """Executes a scenario definition and streams ticks to the engine."""

    def __init__(
        self,
        definition: ScenarioDefinition,
        run: ScenarioRun,
        emit: callable[[RunTick], None],
    ) -> None:
        self.definition = definition
        self._run = run
        self.emit = emit
        layout = definition.config.layout.to_layout()
        self.simulator = WarehouseSimulator(layout=layout)
        self.service = SimulationService(simulator=self.simulator)
        self.reservations: ReservationManager = self.service.reservations
        self.robots: List[RobotAgent] = []
        self._init_robots()
        self._event_buffer: List[TimelineEvent] = []
        self._visit_counter: Counter[str] = Counter()
        self._fault_timers: Dict[str, datetime] = {}
        self._cycle_times: List[float] = []
        self._active_ticks: Dict[str, int] = defaultdict(int)
        self._total_ticks: int = 0
        self._packages_spawned: int = 0
        self._packages_delivered: int = 0
        self._sla_breaches: int = 0
        self._start_times: Dict[str, datetime] = {}
        self._last_emit_at: Optional[datetime] = None
        self._last_emitted_stage: Optional[RunStage] = None

    def _init_robots(self) -> None:
        fleet = self.definition.config.fleet
        positions = list(fleet.starting_positions)
        if not positions:
            # default to first column spacing
            for idx in range(fleet.total_robots):
                positions.append((idx % 3, idx))
        for idx in range(fleet.total_robots):
            robot_id = f"AGV-{idx + 1}"
            start = positions[idx % len(positions)]
            agent = RobotAgent(agent_id=robot_id, start_pos=start, color="#3b82f6", mqtt_manager=_NoOpMQTT(robot_id))
            self.robots.append(agent)

    def _record_event(self, event_type: str, message: str, **payload: Any) -> None:
        event = TimelineEvent(timestamp=datetime.utcnow(), type=event_type, message=message, payload=payload)
        self._run.timeline.append(event)
        self._event_buffer.append(event)

    def _emit_tick(self, stage: RunStage, elapsed_seconds: float, *, force: bool = False) -> None:
        snapshot = self.service.snapshot(robot.telemetry() for robot in self.robots)
        snapshot = WarehouseSnapshot(
            timestamp=datetime.utcnow(),
            packages=snapshot.packages,
            reservations=snapshot.reservations,
            robots=[robot.telemetry() for robot in self.robots],
        )
        self._run.last_snapshot = snapshot
        heatmap = dict(self._visit_counter)
        metrics = self._calculate_metrics(elapsed_seconds)
        self._run.metrics = metrics
        self._run.heatmap = heatmap
        now = datetime.utcnow()
        should_emit = force or self._last_emit_at is None
        if not should_emit and self._last_emit_at is not None:
            should_emit = (now - self._last_emit_at).total_seconds() >= UPDATE_INTERVAL_SECONDS
        if self._last_emitted_stage != stage:
            should_emit = True
        if not should_emit:
            return
        self._last_emit_at = now
        self._last_emitted_stage = stage
        recent = list(self._event_buffer)
        self._event_buffer.clear()
        tick = RunTick(stage=stage, elapsed_seconds=elapsed_seconds, state=snapshot, metrics=metrics, heatmap=heatmap, recent_events=recent)
        self.emit(tick)

    def _calculate_metrics(self, elapsed_seconds: float) -> RunMetrics:
        throughput = 0.0
        if elapsed_seconds > 0:
            throughput = (self._packages_delivered / elapsed_seconds) * 3600.0
        avg_cycle = sum(self._cycle_times) / len(self._cycle_times) if self._cycle_times else 0.0
        total_ticks = max(self._total_ticks, 1)
        active = sum(1 for robot in self.robots if robot.state != RobotState.IDLE)
        utilization = sum(self._active_ticks.values()) / (total_ticks * len(self.robots)) if self.robots else 0.0
        fault_ratio = len([r for r in self.robots if r.state == RobotState.FAULTED]) / len(self.robots) if self.robots else 0.0
        queue_depth = sum(1 for pkg in self.simulator.packages if pkg.status != PackageStatus.DELIVERED)
        return RunMetrics(
            throughput_per_hour=throughput,
            sla_breaches=self._sla_breaches,
            average_cycle_time_seconds=avg_cycle,
            active_robots=active,
            utilization=utilization,
            fault_ratio=fault_ratio,
            queue_depth=queue_depth,
            delivered=self._packages_delivered,
            spawned=self._packages_spawned,
        )

    def _spawn_packages(self, tick_seconds: float) -> None:
        demand = self.definition.config.demand
        expected = demand.packages_per_hour * (tick_seconds / 3600.0)
        probability = min(expected, 1.0)
        trials = max(1, int(expected // 1))
        spawns = 0
        for _ in range(trials):
            if random.random() < probability:
                package = self.service.spawn_package()
                if package:
                    self._packages_spawned += 1
                    self._record_event("package_spawned", "Package queued", package_id=package.id)
                    spawns += 1
        if spawns == 0 and expected > 1.0:
            # if rate is high ensure at least one spawn to avoid starvation
            package = self.service.spawn_package()
            if package:
                self._packages_spawned += 1
                self._record_event("package_spawned", "Package queued", package_id=package.id)

    def _assign_jobs(self) -> None:
        telemetry = [robot.telemetry() for robot in self.robots]
        assignments = self.service.assign_jobs(telemetry)
        for robot in self.robots:
            assigned = assignments.get(robot.id)
            if assigned and robot.state == RobotState.IDLE:
                robot.assign_job(assigned)
                path = self.service.plan_path(robot.position, assigned.position)
                if path:
                    robot.set_path(path)
                else:
                    self._record_event("assignment_failed", "Unable to plan path to pickup", robot_id=robot.id, package_id=assigned.id)

    def _plan_deliveries(self) -> None:
        for robot in self.robots:
            if robot.state == RobotState.DELIVERING and (not robot.path or robot.path_index >= len(robot.path)):
                dropoff = self.service.dropoff_for(robot.position)
                path = self.service.plan_path(robot.position, dropoff)
                if path:
                    robot.set_path(path)
                else:
                    self._record_event("dropoff_blocked", "Unable to plan path to dropoff", robot_id=robot.id)

    def _maybe_fault(self, tick_seconds: float) -> None:
        profile = self.definition.config.failures
        if profile.fault_probability_per_hour <= 0:
            return
        probability = profile.fault_probability_per_hour * (tick_seconds / 3600.0)
        for robot in self.robots:
            if robot.state == RobotState.FAULTED:
                recovery_deadline = self._fault_timers.get(robot.id)
                if recovery_deadline and datetime.utcnow() >= recovery_deadline:
                    robot.recover()
                    self.service.clear_fault(robot.id)
                    self._record_event("robot_recovered", "Robot recovered from fault", robot_id=robot.id)
                    self._fault_timers.pop(robot.id, None)
                continue
            if random.random() < probability:
                package_id = robot.mark_faulted()
                deadline = datetime.utcnow() + timedelta(minutes=profile.mean_recovery_minutes)
                self._fault_timers[robot.id] = deadline
                if package_id:
                    self.service.clear_assignment(robot.id)
                    self.service.release_reservation(robot.id)
                self._record_event("robot_faulted", "Robot entered fault state", robot_id=robot.id, package_id=package_id)

    def _update_robots(self) -> None:
        for robot in self.robots:
            previous_position = robot.position
            delivered_id = robot.update(self.reservations)
            if delivered_id:
                self.service.complete_package(delivered_id)
                self._packages_delivered += 1
                cycle_start = self._start_times.pop(delivered_id, None)
                if cycle_start:
                    cycle_time = (datetime.utcnow() - cycle_start).total_seconds()
                    self._cycle_times.append(cycle_time)
                    demand = self.definition.config.demand
                    for priority, sla in demand.sla_minutes.items():
                        if cycle_time > sla * 60:
                            self._sla_breaches += 1
                            break
                self._record_event("package_delivered", "Package delivered", package_id=delivered_id, robot_id=robot.id)
            if robot.state in (RobotState.FETCHING, RobotState.DELIVERING):
                self._active_ticks[robot.id] += 1
            if robot.current_job and robot.current_job.id not in self._start_times:
                self._start_times[robot.current_job.id] = datetime.utcnow()
            if previous_position != robot.position:
                key = f"{robot.position.x}:{robot.position.y}"
                self._visit_counter[key] += 1
            if robot.state == RobotState.IDLE:
                self.service.release_reservation(robot.id)

    async def run(self) -> None:
        config = self.definition.config
        tick_seconds = config.operations.cadence_ms / 1000.0
        runtime = timedelta(minutes=config.horizon.duration_minutes)
        warmup = timedelta(minutes=config.operations.warmup_minutes)
        started = datetime.utcnow()
        self._run.started_at = started
        stage = RunStage.WARMING_UP
        elapsed = 0.0
        try:
            while True:
                now = datetime.utcnow()
                elapsed = (now - started).total_seconds()
                stage_changed = False
                if stage == RunStage.WARMING_UP and now - started >= warmup:
                    stage = RunStage.RUNNING
                    stage_changed = True
                    self._record_event("stage_transition", "Run entered active window")
                if stage == RunStage.RUNNING and now - started >= runtime:
                    break
                self._total_ticks += 1
                self._spawn_packages(tick_seconds)
                self._assign_jobs()
                self._plan_deliveries()
                self._maybe_fault(tick_seconds)
                self._update_robots()
                self._emit_tick(stage, elapsed, force=stage_changed)
                await asyncio.sleep(tick_seconds / max(config.operations.time_scale, 1))
            stage = RunStage.COMPLETED
            self._run.stage = stage
            self._run.completed_at = datetime.utcnow()
            self._emit_tick(stage, (datetime.utcnow() - started).total_seconds(), force=True)
        except asyncio.CancelledError:
            self._run.stage = RunStage.CANCELLED
            self._run.completed_at = datetime.utcnow()
            self._record_event("run_cancelled", "Run cancelled by operator")
            self._emit_tick(RunStage.CANCELLED, (datetime.utcnow() - started).total_seconds(), force=True)
            raise
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            self._run.stage = RunStage.FAILED
            self._run.error = str(exc)
            self._run.completed_at = datetime.utcnow()
            self._record_event("run_failed", "Run failed", error=str(exc))
            self._emit_tick(RunStage.FAILED, (datetime.utcnow() - started).total_seconds(), force=True)
            raise


class ScenarioEngine:
    """Coordinates scenario definitions, runs, and live streaming."""

    def __init__(self) -> None:
        self._scenarios: Dict[str, ScenarioDefinition] = {}
        self._runs: Dict[str, ScenarioRun] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._subscribers: Dict[str, List[asyncio.Queue[RunTick]]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._bootstrap_default_scenarios()

    def _bootstrap_default_scenarios(self) -> None:
        if self._scenarios:
            return
        moderate = ScenarioConfig(
            name="Peak Hour",
            description="High throughput load with dense arrivals",
            layout=LayoutConfig(
                width=24,
                height=16,
                cell_size=32,
                pickup_zones=[(1, 4), (1, 6), (1, 8), (1, 10)],
                dropoff_zones=[(22, 5), (22, 7), (22, 9)],
                obstacles=[(10, y) for y in range(2, 14)],
                charging_zones=[(2, 2), (2, 13)],
            ),
            fleet=FleetConfig(total_robots=6, classes=[FleetClassConfig(name="AGV", speed_cells_per_tick=1.0, payload_capacity=1, battery_capacity_minutes=240)]),
            demand=DemandProfile(packages_per_hour=120.0, priority_mix={"standard": 0.6, "express": 0.4}),
            operations=OperationsProfile(shift_minutes=120, cadence_ms=400, warmup_minutes=2, time_scale=12.0),
            failures=FailureProfile(fault_probability_per_hour=0.12, mean_recovery_minutes=3.0),
            optimization=OptimizationProfile(),
            horizon=HorizonProfile(duration_minutes=30),
        )
        outage = ScenarioConfig(
            name="Robot Outage",
            description="Simulate cascading robot failures",
            layout=LayoutConfig(
                width=20,
                height=14,
                cell_size=32,
                pickup_zones=[(1, 3), (1, 6), (1, 9)],
                dropoff_zones=[(18, 4), (18, 8)],
                obstacles=[(8, y) for y in range(1, 13)],
                charging_zones=[(3, 12)],
            ),
            fleet=FleetConfig(total_robots=4, classes=[FleetClassConfig(name="Standard", speed_cells_per_tick=0.8, payload_capacity=1, battery_capacity_minutes=180)]),
            demand=DemandProfile(packages_per_hour=80.0, priority_mix={"standard": 0.8, "express": 0.2}),
            operations=OperationsProfile(shift_minutes=90, cadence_ms=500, warmup_minutes=1, time_scale=10.0),
            failures=FailureProfile(fault_probability_per_hour=0.35, mean_recovery_minutes=8.0),
            optimization=OptimizationProfile(),
            horizon=HorizonProfile(duration_minutes=20),
        )
        rush = ScenarioConfig(
            name="Priority Rush",
            description="Express-heavy surge with tight SLAs",
            layout=LayoutConfig(
                width=22,
                height=18,
                cell_size=32,
                pickup_zones=[(2, 4), (2, 8), (2, 12)],
                dropoff_zones=[(20, 5), (20, 9), (20, 13)],
                obstacles=[(11, y) for y in range(3, 15)],
                charging_zones=[(3, 16), (4, 16)],
            ),
            fleet=FleetConfig(total_robots=5, classes=[FleetClassConfig(name="Express", speed_cells_per_tick=1.2, payload_capacity=1, battery_capacity_minutes=200)]),
            demand=DemandProfile(packages_per_hour=150.0, priority_mix={"standard": 0.3, "express": 0.7}, sla_minutes={"standard": 25.0, "express": 8.0}),
            operations=OperationsProfile(shift_minutes=120, cadence_ms=350, warmup_minutes=1, time_scale=14.0),
            failures=FailureProfile(fault_probability_per_hour=0.2, mean_recovery_minutes=4.0),
            optimization=OptimizationProfile(),
            horizon=HorizonProfile(duration_minutes=25),
        )
        for scenario in (moderate, outage, rush):
            self._register_scenario(scenario)

    def _register_scenario(self, config: ScenarioConfig) -> ScenarioDefinition:
        scenario_id = str(uuid.uuid4())
        definition = ScenarioDefinition(id=scenario_id, created_at=datetime.utcnow(), config=config)
        self._scenarios[scenario_id] = definition
        return definition

    async def list_scenarios(self) -> List[ScenarioDefinition]:
        return list(self._scenarios.values())

    async def get_scenario(self, scenario_id: str) -> ScenarioDefinition:
        if scenario_id not in self._scenarios:
            raise KeyError(scenario_id)
        return self._scenarios[scenario_id]

    async def create_scenario(self, config: ScenarioConfig) -> ScenarioDefinition:
        return self._register_scenario(config)

    async def launch_run(self, scenario_id: str) -> ScenarioRun:
        definition = await self.get_scenario(scenario_id)
        run_id = str(uuid.uuid4())
        run = ScenarioRun(id=run_id, scenario_id=scenario_id, stage=RunStage.QUEUED, created_at=datetime.utcnow())
        self._runs[run_id] = run

        async with self._lock:
            task = asyncio.create_task(self._execute_run(definition, run))
            self._tasks[run_id] = task
        return run

    async def _execute_run(self, definition: ScenarioDefinition, run: ScenarioRun) -> None:
        queue = self._subscribers.setdefault(run.id, [])

        def emit(tick: RunTick) -> None:
            run.stage = tick.stage
            run.last_snapshot = tick.state
            run.metrics = tick.metrics
            run.heatmap = tick.heatmap
            for subscriber in list(queue):
                subscriber.put_nowait(tick)

        runner = ScenarioRunner(definition, run, emit)
        run.stage = RunStage.WARMING_UP
        try:
            await runner.run()
        finally:
            elapsed_reference = run.completed_at or datetime.utcnow()
            elapsed_seconds = (elapsed_reference - run.created_at).total_seconds()
            for subscriber in list(queue):
                subscriber.put_nowait(
                    RunTick(
                        stage=run.stage,
                        elapsed_seconds=elapsed_seconds,
                        state=run.last_snapshot
                        or WarehouseSnapshot(timestamp=datetime.utcnow(), packages=[], reservations=[], robots=[]),
                        metrics=run.metrics,
                        heatmap=run.heatmap,
                        recent_events=[],
                    )
                )
            self._tasks.pop(run.id, None)

    async def get_run(self, run_id: str) -> ScenarioRun:
        if run_id not in self._runs:
            raise KeyError(run_id)
        return self._runs[run_id]

    async def list_runs(self) -> List[ScenarioRun]:
        return sorted(self._runs.values(), key=lambda r: r.created_at, reverse=True)

    async def get_timeline(self, run_id: str) -> List[TimelineEvent]:
        run = await self.get_run(run_id)
        return list(run.timeline)

    async def cancel_run(self, run_id: str) -> None:
        task = self._tasks.get(run_id)
        if task and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    async def subscribe(self, run_id: str) -> AsyncIterator[RunTick]:
        queue: asyncio.Queue[RunTick] = asyncio.Queue()
        self._subscribers.setdefault(run_id, []).append(queue)
        try:
            while True:
                tick = await queue.get()
                yield tick
        finally:
            self._subscribers[run_id].remove(queue)


__all__ = [
    "ScenarioEngine",
    "ScenarioDefinition",
    "ScenarioRun",
    "ScenarioConfig",
    "RunStage",
    "RunTick",
    "RunMetrics",
    "TimelineEvent",
]
