import type { RobotHealth } from "../types";

interface RobotHealthListProps {
  health: RobotHealth[];
}

function formatStatus(status: RobotHealth): string {
  return status.faulted ? "Faulted" : "Healthy";
}

export function RobotHealthList({ health }: RobotHealthListProps) {
  return (
    <section className="panel">
      <header className="panel-header">
        <h2>Robot Health</h2>
        <p className="panel-caption">Live telemetry indicating stalled or faulted robots.</p>
      </header>

      {health.length === 0 ? (
        <p className="empty-state">No robots registered yet.</p>
      ) : (
        <ul className="health-list">
          {health.map((item) => (
            <li key={item.robot_id} className={item.faulted ? "health faulted" : "health healthy"}>
              <span className="health-id">{item.robot_id}</span>
              <span className="health-state">{formatStatus(item)}</span>
              <span className="health-meta">Stalled ticks: {item.stalled_ticks}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
