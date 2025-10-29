import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { fetchAnalyticsScenarios } from "../api";
import { WarehouseCanvas } from "../components/WarehouseCanvas";
import type { AnalyticsRunPoint, AnalyticsScenarioSummary } from "../types";

function sortSeries(series: AnalyticsRunPoint[]): AnalyticsRunPoint[] {
  return [...series].sort((a, b) => {
    const aTime = a.started_at ? new Date(a.started_at).getTime() : 0;
    const bTime = b.started_at ? new Date(b.started_at).getTime() : 0;
    return aTime - bTime;
  });
}

function ThroughputTrendChart({ series }: { series: AnalyticsRunPoint[] }) {
  if (!series.length) {
    return <p className="empty-state">Launch a run to unlock throughput analytics.</p>;
  }

  const sorted = sortSeries(series);
  const width = 720;
  const height = 220;
  const margin = 32;
  const maxValue = Math.max(...sorted.map((item) => item.throughput_per_hour), 1);
  const step = sorted.length > 1 ? (width - margin * 2) / (sorted.length - 1) : 0;
  const points = sorted.map((item, index) => {
    const value = item.throughput_per_hour;
    const x = margin + step * index;
    const normalized = value / maxValue;
    const y = height - margin - normalized * (height - margin * 2);
    return `${x},${y}`;
  });

  const areaPoints = [`${margin},${height - margin}`, ...points, `${margin + step * Math.max(sorted.length - 1, 0)},${height - margin}`];

  return (
    <svg className="trend-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Throughput trend">
      <defs>
        <linearGradient id="throughputGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="rgba(59, 130, 246, 0.45)" />
          <stop offset="100%" stopColor="rgba(59, 130, 246, 0)" />
        </linearGradient>
      </defs>
      <path d={`M${areaPoints.join(" L ")} Z`} fill="url(#throughputGradient)" />
      <polyline points={points.join(" ")} fill="none" stroke="rgba(96, 165, 250, 0.95)" strokeWidth={3} strokeLinejoin="round" />
      {sorted.map((item, index) => {
        const x = margin + step * index;
        const y = height - margin - (item.throughput_per_hour / maxValue) * (height - margin * 2);
        return <circle key={item.run_id} cx={x} cy={y} r={4.5} fill="#60a5fa" stroke="#0f172a" strokeWidth={2} />;
      })}
      <g className="trend-axis">
        <line x1={margin} y1={height - margin} x2={width - margin} y2={height - margin} stroke="rgba(148, 163, 184, 0.3)" />
        <line x1={margin} y1={margin} x2={margin} y2={height - margin} stroke="rgba(148, 163, 184, 0.3)" />
        <text x={margin} y={margin - 6} className="trend-axis-label">Throughput/hr</text>
        <text x={width - margin} y={height - margin + 24} textAnchor="end" className="trend-axis-label">Most recent runs</text>
      </g>
    </svg>
  );
}

function UtilizationStack({
  series,
  fleetSize,
}: {
  series: AnalyticsRunPoint[];
  fleetSize: number;
}) {
  if (!series.length) {
    return <p className="empty-state">Launch a run to see fleet utilization patterns.</p>;
  }
  const sorted = sortSeries(series).slice(-12);

  return (
    <div className="stack-list">
      {sorted.map((item, index) => {
        const activeRatio = fleetSize ? Math.min(item.active_robots / fleetSize, 1) : 0;
        const idleRatio = Math.max(1 - activeRatio, 0);
        const timestamp = item.started_at ? new Date(item.started_at).toLocaleString() : "Not started";
        return (
          <div className="stack-row" key={item.run_id}>
            <div className="stack-row-header">
              <span>Run {sorted.length - index}</span>
              <span>{timestamp}</span>
            </div>
            <div className="stack-bar" title={`Active ${item.active_robots}/${fleetSize} robots`}>
              <span className="stack-segment active" style={{ width: `${activeRatio * 100}%` }} />
              <span className="stack-segment idle" style={{ width: `${idleRatio * 100}%` }} />
            </div>
            <div className="stack-meta">
              <span>{item.active_robots} active</span>
              <span>{(item.utilization * 100).toFixed(1)}% utilization</span>
              <span>{(item.fault_ratio * 100).toFixed(1)}% fault ratio</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function AnalyticsDashboard() {
  const [scenarios, setScenarios] = useState<AnalyticsScenarioSummary[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const data = await fetchAnalyticsScenarios();
        if (!mounted) {
          return;
        }
        setScenarios(data);
        setSelectedScenarioId((previous) => previous ?? data[0]?.scenario_id ?? null);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unable to load analytics";
        setError(message);
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const selectedScenario = useMemo(
    () => scenarios.find((item) => item.scenario_id === selectedScenarioId) ?? null,
    [scenarios, selectedScenarioId],
  );

  const topHotspots = useMemo(() => {
    if (!selectedScenario) {
      return [];
    }
    return Object.entries(selectedScenario.heatmap.cells)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8);
  }, [selectedScenario]);

  return (
    <div className="analytics-app">
      <header className="analytics-header">
        <div>
          <h1>Strategic Analytics Hub</h1>
          <p>Benchmark throughput, utilisation, and grid congestion across every orchestration scenario.</p>
        </div>
        <div className="header-actions">
          <Link to="/" className="ghost nav-link">Back to live ops</Link>
        </div>
      </header>

      <main className="analytics-body">
        {isLoading ? (
          <div className="empty-state hero">
            <h2>Loading enterprise insights…</h2>
            <p>Crunching fleet telemetry, metrics, and congestion traces.</p>
          </div>
        ) : error ? (
          <div className="empty-state hero">
            <h2>Analytics unavailable</h2>
            <p>{error}</p>
          </div>
        ) : !selectedScenario ? (
          <div className="empty-state hero">
            <h2>No scenarios yet</h2>
            <p>Create and execute a scenario to populate analytics.</p>
          </div>
        ) : (
          <div className="analytics-content">
            <section className="analytics-controls">
              <label htmlFor="scenario-analytics-select">
                Scenario
                <select
                  id="scenario-analytics-select"
                  value={selectedScenarioId ?? ""}
                  onChange={(event) => setSelectedScenarioId(event.target.value)}
                >
                  {scenarios.map((scenario) => (
                    <option key={scenario.scenario_id} value={scenario.scenario_id}>
                      {scenario.scenario_name} · {scenario.total_runs} runs
                    </option>
                  ))}
                </select>
              </label>
              <div className="analytics-metadata">
                <span>Fleet size: {selectedScenario.fleet_total_robots} robots</span>
                <span>Last run: {selectedScenario.last_run_at ? new Date(selectedScenario.last_run_at).toLocaleString() : "—"}</span>
              </div>
            </section>

            <section className="stats-grid">
              <article className="stats-card">
                <h3>Avg throughput</h3>
                <p>{selectedScenario.avg_throughput_per_hour.toFixed(1)}<span className="stats-card-suffix">/hr</span></p>
              </article>
              <article className="stats-card">
                <h3>Avg utilisation</h3>
                <p>{(selectedScenario.avg_utilization * 100).toFixed(1)}<span className="stats-card-suffix">%</span></p>
              </article>
              <article className="stats-card">
                <h3>Active robots</h3>
                <p>{selectedScenario.avg_active_robots.toFixed(1)}</p>
              </article>
              <article className="stats-card">
                <h3>Delivered packages</h3>
                <p>{selectedScenario.total_delivered}</p>
              </article>
              <article className="stats-card">
                <h3>Fault ratio</h3>
                <p>{(selectedScenario.avg_fault_ratio * 100).toFixed(2)}<span className="stats-card-suffix">%</span></p>
              </article>
            </section>

            <section className="analytics-panel">
              <header className="panel-header">
                <div>
                  <h2>Throughput trend</h2>
                  <p className="panel-caption">Hourly throughput indexed by run execution.</p>
                </div>
              </header>
              <ThroughputTrendChart series={selectedScenario.throughput_series} />
            </section>

            <section className="analytics-panel">
              <header className="panel-header">
                <div>
                  <h2>Fleet utilisation stack</h2>
                  <p className="panel-caption">Active vs. idle robots across the most recent twelve runs.</p>
                </div>
              </header>
              <UtilizationStack series={selectedScenario.utilization_series} fleetSize={selectedScenario.fleet_total_robots} />
            </section>

            <section className="analytics-panel heatmap-panel">
              <header className="panel-header">
                <div>
                  <h2>Congestion heatmap</h2>
                  <p className="panel-caption">Accumulated cell visits across every completed run.</p>
                </div>
              </header>
              <WarehouseCanvas
                layout={selectedScenario.layout}
                packages={[]}
                robots={[]}
                reservations={[]}
                heatmap={selectedScenario.heatmap.cells}
                showHeatmap
              />
              <div className="hotspot-list">
                <h3>Top hotspots</h3>
                {topHotspots.length ? (
                  <ul>
                    {topHotspots.map(([cell, value]) => (
                      <li key={cell}>
                        <span>{cell.replace(":", ", ")}</span>
                        <strong>{value}</strong>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="empty-state">No congestion detected yet.</p>
                )}
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
