import type { ScenarioRun, ScenarioSummary } from "../types";
import { StageIndicator } from "./StageIndicator";

interface RunHistoryListProps {
  runs: ScenarioRun[];
  scenarios: ScenarioSummary[];
  activeRunId?: string;
  onSelectRun: (runId: string) => void;
}

export function RunHistoryList({ runs, scenarios, activeRunId, onSelectRun }: RunHistoryListProps) {
  if (!runs.length) {
    return <p className="empty-state">Run history will appear once scenarios are launched.</p>;
  }
  return (
    <ul className="run-list">
      {runs.map((run) => {
        const scenario = scenarios.find((item) => item.id === run.scenario_id);
        return (
          <li key={run.id} className={run.id === activeRunId ? "active" : ""}>
            <button type="button" onClick={() => onSelectRun(run.id)}>
              <div className="run-list-header">
                <span className="run-list-name">{scenario?.config.name ?? "Scenario"}</span>
                <StageIndicator stage={run.stage} />
              </div>
              <div className="run-list-meta">
                <span>{new Date(run.created_at).toLocaleTimeString()}</span>
                <span>{run.metrics.delivered} delivered</span>
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
