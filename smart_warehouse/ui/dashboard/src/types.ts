export interface GridPosition {
  x: number;
  y: number;
}

export interface Layout {
  width: number;
  height: number;
  cell_size: number;
  obstacles: GridPosition[];
  pickup_zones: GridPosition[];
  dropoff_zones: GridPosition[];
  charging_zones?: GridPosition[];
}

export interface SimulationPackage {
  id: string;
  position: GridPosition;
  status: string;
  assigned_robot: string | null;
  created_at: string;
}

export interface Reservation {
  robot_id: string;
  position: GridPosition;
  expires_at: string;
}

export interface RobotTelemetry {
  robot_id: string;
  state: string;
  position: GridPosition;
  battery_level: number;
  current_job: string | null;
  path: GridPosition[];
}

export interface SimulationState {
  packages: SimulationPackage[];
  reservations: Reservation[];
  robots: RobotTelemetry[];
  layout: Layout;
}

export interface RobotHealth {
  robot_id: string;
  stalled_ticks: number;
  faulted: boolean;
}

export interface SimulationEvent {
  id: number;
  created_at: string;
  type: string;
  payload: Record<string, unknown>;
  package_id?: string | null;
  robot_id?: string | null;
  robot_state?: string | null;
}

export type RunStage = "QUEUED" | "WARMING_UP" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED";

export interface ScenarioLayoutConfig {
  width: number;
  height: number;
  cell_size: number;
  pickup_zones: GridPosition[];
  dropoff_zones: GridPosition[];
  obstacles: GridPosition[];
  charging_zones?: GridPosition[];
}

export interface FleetClassConfig {
  name: string;
  speed_cells_per_tick: number;
  payload_capacity: number;
  battery_capacity_minutes: number;
}

export interface FleetConfig {
  total_robots: number;
  classes: FleetClassConfig[];
  starting_positions: GridPosition[];
}

export interface DemandProfile {
  packages_per_hour: number;
  priority_mix: Record<string, number>;
  sla_minutes: Record<string, number>;
}

export interface OperationsProfile {
  shift_minutes: number;
  cadence_ms: number;
  warmup_minutes: number;
  time_scale: number;
}

export interface FailureProfile {
  fault_probability_per_hour: number;
  mean_recovery_minutes: number;
}

export interface OptimizationProfile {
  planner: string;
  assignment_policy: string;
  reservation_horizon: number;
}

export interface HorizonProfile {
  duration_minutes: number;
  stop_on_completion: boolean;
}

export interface ScenarioConfig {
  name: string;
  description: string;
  layout: ScenarioLayoutConfig;
  fleet: FleetConfig;
  demand: DemandProfile;
  operations: OperationsProfile;
  failures: FailureProfile;
  optimization: OptimizationProfile;
  horizon: HorizonProfile;
  metadata: Record<string, unknown>;
}

export interface ScenarioSummary {
  id: string;
  created_at: string;
  config: ScenarioConfig;
}

export interface RunMetrics {
  throughput_per_hour: number;
  sla_breaches: number;
  average_cycle_time_seconds: number;
  active_robots: number;
  utilization: number;
  fault_ratio: number;
  queue_depth: number;
  delivered: number;
  spawned: number;
}

export interface TimelineEventDetail {
  timestamp: string;
  type: string;
  message: string;
  payload: Record<string, unknown>;
}

export interface ScenarioRun {
  id: string;
  scenario_id: string;
  stage: RunStage;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  metrics: RunMetrics;
  heatmap: Record<string, number>;
  error: string | null;
}

export interface ScenarioRunDetail extends ScenarioRun {
  state?: SimulationState;
  timeline: TimelineEventDetail[];
}

export interface RunTick {
  stage: RunStage;
  elapsed_seconds: number;
  state: SimulationState;
  metrics: RunMetrics;
  heatmap: Record<string, number>;
  recent_events: TimelineEventDetail[];
}

export interface AnalyticsHeatmapSummary {
  total_visits: number;
  max_visits: number;
  cells: Record<string, number>;
}

export interface AnalyticsRunPoint {
  run_id: string;
  scenario_id: string;
  scenario_name: string;
  started_at: string | null;
  completed_at: string | null;
  throughput_per_hour: number;
  delivered: number;
  sla_breaches: number;
  utilization: number;
  active_robots: number;
  idle_robots: number;
  fault_ratio: number;
}

export interface AnalyticsScenarioSummary {
  scenario_id: string;
  scenario_name: string;
  description: string;
  fleet_total_robots: number;
  total_runs: number;
  avg_throughput_per_hour: number;
  avg_utilization: number;
  avg_active_robots: number;
  total_delivered: number;
  avg_fault_ratio: number;
  throughput_series: AnalyticsRunPoint[];
  utilization_series: AnalyticsRunPoint[];
  heatmap: AnalyticsHeatmapSummary;
  layout: Layout;
  last_run_at: string | null;
}
