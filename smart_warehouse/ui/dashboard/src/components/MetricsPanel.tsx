import { StatsCard } from "./StatsCard";
import type { RunMetrics } from "../types";

interface MetricsPanelProps {
  metrics: RunMetrics | null;
}

export function MetricsPanel({ metrics }: MetricsPanelProps) {
  if (!metrics) {
    return (
      <div className="panel">
        <header className="panel-header">
          <h2>Key Metrics</h2>
          <p className="panel-caption">Metrics will appear once the simulation is running.</p>
        </header>
        <p className="empty-state">Awaiting live data.</p>
      </div>
    );
  }

  return (
    <section className="panel">
      <header className="panel-header">
        <div>
          <h2>Key Metrics</h2>
          <p className="panel-caption">Real-time KPIs refreshed each tick.</p>
        </div>
      </header>
      <div className="stats-grid">
        <StatsCard title="Throughput / hr" value={metrics.throughput_per_hour} format="decimal" />
        <StatsCard title="Delivered" value={metrics.delivered} />
        <StatsCard title="Queue depth" value={metrics.queue_depth} />
        <StatsCard title="Utilization" value={metrics.utilization * 100} suffix="%" format="decimal" />
        <StatsCard title="Fault ratio" value={metrics.fault_ratio * 100} suffix="%" format="decimal" />
        <StatsCard title="SLA breaches" value={metrics.sla_breaches} />
        <StatsCard title="Avg. cycle (m)" value={metrics.average_cycle_time_seconds / 60} format="decimal" />
        <StatsCard title="Spawned" value={metrics.spawned} />
      </div>
    </section>
  );
}
