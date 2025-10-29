import type { ScenarioSummary } from "../types";

interface ScenarioCatalogProps {
  scenarios: ScenarioSummary[];
  selectedScenarioId?: string;
  launchingScenarioId?: string | null;
  onSelect: (scenario: ScenarioSummary) => void;
  onLaunch: (scenario: ScenarioSummary) => void;
}

export function ScenarioCatalog({ scenarios, selectedScenarioId, launchingScenarioId, onSelect, onLaunch }: ScenarioCatalogProps) {
  if (!scenarios.length) {
    return <p className="empty-state">No scenarios captured yet. Create one to get started.</p>;
  }

  return (
    <ul className="scenario-grid">
      {scenarios.map((scenario) => {
        const { config } = scenario;
        const isActive = scenario.id === selectedScenarioId;
        const isLaunching = scenario.id === launchingScenarioId;
        return (
          <li key={scenario.id} className={`scenario-card${isActive ? " active" : ""}`}>
            <header>
              <div>
                <h3>{config.name}</h3>
                <p>{config.description}</p>
              </div>
              <span className="scenario-created">{new Date(scenario.created_at).toLocaleString()}</span>
            </header>
            <div className="scenario-body">
              <div>
                <span className="scenario-label">Layout</span>
                <strong>{config.layout.width}×{config.layout.height}</strong>
              </div>
              <div>
                <span className="scenario-label">Fleet</span>
                <strong>{config.fleet.total_robots} robots</strong>
              </div>
              <div>
                <span className="scenario-label">Demand</span>
                <strong>{config.demand.packages_per_hour} pph</strong>
              </div>
              <div>
                <span className="scenario-label">Horizon</span>
                <strong>{config.horizon.duration_minutes} min</strong>
              </div>
            </div>
            <footer>
              <button type="button" className="ghost" onClick={() => onSelect(scenario)}>
                {isActive ? "Selected" : "Inspect"}
              </button>
              <button type="button" onClick={() => onLaunch(scenario)} disabled={isLaunching}>
                {isLaunching ? "Launching..." : "Launch run"}
              </button>
            </footer>
          </li>
        );
      })}
    </ul>
  );
}
