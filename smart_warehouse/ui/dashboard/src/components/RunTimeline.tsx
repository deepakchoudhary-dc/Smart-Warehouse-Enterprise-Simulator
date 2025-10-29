import type { TimelineEventDetail } from "../types";

interface RunTimelineProps {
  events: TimelineEventDetail[];
}

export function RunTimeline({ events }: RunTimelineProps) {
  return (
    <section className="panel event-panel">
      <header className="panel-header">
        <div>
          <h2>Run Timeline</h2>
          <p className="panel-caption">Latest operational events, faults, and completions.</p>
        </div>
      </header>
      {events.length === 0 ? (
        <p className="empty-state">No telemetry received yet.</p>
      ) : (
        <ul className="event-list">
          {events.map((event, index) => (
            <li key={`${event.timestamp}-${index}`} className="event-item">
              <div className="event-meta">
                <span className="event-type">{event.type}</span>
                <time>{new Date(event.timestamp).toLocaleTimeString()}</time>
              </div>
              <p className="event-message">{event.message}</p>
              {Object.keys(event.payload || {}).length > 0 ? (
                <pre className="event-payload">{JSON.stringify(event.payload, null, 2)}</pre>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
