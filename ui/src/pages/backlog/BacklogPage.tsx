import "./backlog.css";

const backlogRows = [
  { id: "EVT-9912", partition: "Claims", status: "pending", age: "2m", batch: "BATCH-08" },
  { id: "EVT-9908", partition: "Tax", status: "retry", age: "5m", batch: "BATCH-08" },
  { id: "EVT-9896", partition: "Policy", status: "pending", age: "9m", batch: "BATCH-07" },
  { id: "EVT-9881", partition: "Finance", status: "staged", age: "12m", batch: "BATCH-06" },
  { id: "EVT-9875", partition: "Claims", status: "retry", age: "15m", batch: "BATCH-06" },
  { id: "EVT-9862", partition: "Audit", status: "pending", age: "21m", batch: "BATCH-05" },
];

const dispatchQueue = [
  "BATCH-08 · 6 events",
  "BATCH-07 · 5 events",
  "BATCH-06 · 4 events",
  "BATCH-05 · 3 events",
];

export function BacklogPage() {
  return (
    <section className="backlog-page">
      <header className="backlog-page-header">
        <div className="backlog-page-copy">
          <h2>Backlog</h2>
        </div>
      </header>

      <section className="backlog-status-strip">
        <article className="backlog-status-card">
          <span>Pending</span>
          <strong>24</strong>
        </article>
        <article className="backlog-status-card">
          <span>Batches</span>
          <strong>8</strong>
        </article>
        <article className="backlog-status-card">
          <span>Retry</span>
          <strong>3</strong>
        </article>
        <article className="backlog-status-card is-accent">
          <span>Triggered</span>
          <strong>19</strong>
        </article>
      </section>

      <section className="backlog-main-grid">
        <article className="skeleton-card backlog-table-card">
          <div className="backlog-panel-head">
            <h3>Event Queue</h3>
          </div>
          <div className="backlog-table-scroll">
            <div className="backlog-table">
              <div className="backlog-table-header">
                <span>Event</span>
                <span>Partition</span>
                <span>Status</span>
                <span>Age</span>
                <span>Batch</span>
              </div>
              {backlogRows.map((row) => (
                <div key={row.id} className="backlog-table-row">
                  <strong>{row.id}</strong>
                  <span>{row.partition}</span>
                  <span className={`backlog-inline-status is-${row.status}`}>{row.status}</span>
                  <span>{row.age}</span>
                  <code>{row.batch}</code>
                </div>
              ))}
            </div>
          </div>
        </article>

        <div className="backlog-side-stack">
          <article className="skeleton-card backlog-side-card">
            <div className="backlog-panel-head">
              <h3>Dispatch Queue</h3>
            </div>
            <ul className="backlog-compact-list">
              {dispatchQueue.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>

          <article className="skeleton-card backlog-side-card">
            <div className="backlog-panel-head">
              <h3>Quick Actions</h3>
            </div>
            <div className="backlog-action-grid">
              <button type="button">Assemble batch</button>
              <button type="button">Dispatch selected</button>
              <button type="button">Retry failed</button>
              <button type="button">Drain partition</button>
            </div>
          </article>
        </div>
      </section>

      <section className="backlog-bottom-row">
        <article className="skeleton-card backlog-flow-card">
          <div className="backlog-panel-head">
            <h3>Flow</h3>
          </div>
          <div className="backlog-flow-track">
            <span>Event</span>
            <i />
            <span>Batch</span>
            <i />
            <span>Runtime</span>
          </div>
        </article>
      </section>
    </section>
  );
}
