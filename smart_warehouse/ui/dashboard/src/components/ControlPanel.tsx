interface ControlPanelProps {
  onSpawnPackage: () => void;
  onResetSimulation: () => void;
  onRefreshNow: () => void;
  refreshInterval: number;
  onIntervalChange: (value: number) => void;
  isBusy: boolean;
  lastUpdated: Date | null;
}

const REFRESH_OPTIONS: Array<{ label: string; value: number }> = [
  { label: "1s", value: 1000 },
  { label: "2s", value: 2000 },
  { label: "5s", value: 5000 },
  { label: "10s", value: 10000 },
];

export function ControlPanel({
  onSpawnPackage,
  onResetSimulation,
  onRefreshNow,
  refreshInterval,
  onIntervalChange,
  isBusy,
  lastUpdated,
}: ControlPanelProps) {
  const formattedTimestamp = lastUpdated
    ? `${lastUpdated.toLocaleDateString()} ${lastUpdated.toLocaleTimeString()}`
    : "–";

  return (
    <section className="panel control-panel" aria-label="Simulation controls">
      <header className="panel-header">
        <h2>Controls</h2>
        <p className="panel-caption">Trigger actions and configure auto-refresh cadence.</p>
      </header>

      <div className="control-grid">
        <button type="button" onClick={onSpawnPackage} disabled={isBusy}>
          Spawn Package
        </button>
        <button
          type="button"
          className="secondary"
          onClick={onResetSimulation}
          disabled={isBusy}
        >
          Reset Simulation
        </button>
        <button type="button" className="ghost" onClick={onRefreshNow} disabled={isBusy}>
          Refresh Now
        </button>
      </div>

      <div className="control-meta">
        <label className="control-label" htmlFor="refresh-select">
          Auto-refresh cadence
        </label>
        <select
          id="refresh-select"
          value={refreshInterval}
          onChange={(event) => onIntervalChange(Number(event.target.value))}
        >
          {REFRESH_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <dl className="control-meta">
        <div>
          <dt>Last updated</dt>
          <dd>{formattedTimestamp}</dd>
        </div>
      </dl>
    </section>
  );
}
