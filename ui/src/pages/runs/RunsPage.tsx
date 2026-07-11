import "./runs.css";

export function RunsPage() {
  return (
    <section className="runs-page">
      <header className="runs-page-header">
        <div className="runs-page-copy">
          <h2>Runs</h2>
        </div>
      </header>

      <section className="page-rail-layout">
        <article className="skeleton-card">
          <span className="card-kicker">Ledger</span>
          <h3>Run Timeline List</h3>
          <p>Primary list for filtering runs by partition, status, source, and time.</p>
          <div className="skeleton-bars">
            <span style={{ width: "100%" }} />
            <span style={{ width: "100%" }} />
            <span style={{ width: "100%" }} />
            <span style={{ width: "100%" }} />
            <span style={{ width: "100%" }} />
          </div>
        </article>
        <div className="page-stack">
          <article className="skeleton-card is-dark">
            <span className="card-kicker">Decision</span>
            <h3>Planner Decision Trace</h3>
            <p>Per-turn decision cards, rationale, and stop conditions appear in this rail.</p>
            <ul className="skeleton-list">
              <li />
              <li />
              <li />
            </ul>
          </article>
          <article className="skeleton-card">
            <span className="card-kicker">Artifacts</span>
            <h3>Run Artifacts</h3>
            <p>Request snapshot, decision payloads, and execution records surface here.</p>
            <div className="skeleton-lines">
              <span style={{ width: "82%" }} />
              <span style={{ width: "66%" }} />
              <span style={{ width: "74%" }} />
            </div>
          </article>
        </div>
      </section>
    </section>
  );
}
