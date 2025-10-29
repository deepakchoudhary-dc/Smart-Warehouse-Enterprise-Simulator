import type { SimulationEvent } from "../types";

interface EventTimelineProps {
  events: SimulationEvent[];
  loading: boolean;
  onRefresh: () => void | Promise<void>;
}

export function EventTimeline({ events, loading, onRefresh }: EventTimelineProps) {
  return (
    <section className="panel event-panel">
      <header className="panel-header">
        <div>
          <h2>Event Timeline</h2>
          <p className="panel-caption">Recent activity recorded by the simulation.</p>
        </div>
        <button type="button" className="ghost" onClick={onRefresh} disabled={loading}>
          Refresh
        </button>
      </header>

      {events.length === 0 ? (
        <p className="empty-state">No events captured yet.</p>
      ) : (
        <ul className="event-list">
          {events.map((event) => (
            <li key={event.id} className="event-item">
              <div className="event-meta">
                <span className="event-type">{event.type.replace(/_/g, " ")}</span>
                <time dateTime={event.created_at}>
                  {new Date(event.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                </time>
              </div>
              <div className="event-details">
                {event.robot_id && <span>Robot: {event.robot_id}</span>}
                {event.package_id && <span>Package: {event.package_id}</span>}
                {event.robot_state && <span>State: {event.robot_state}</span>}
              </div>
              {Object.keys(event.payload || {}).length > 0 && (
                <pre className="event-payload">{JSON.stringify(event.payload, null, 2)}</pre>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
