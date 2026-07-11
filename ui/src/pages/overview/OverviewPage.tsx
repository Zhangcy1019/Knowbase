import "./overview.css";

const partitionRows = [
  { name: "Tax", cases: "842", backlog: "6", run: "2m ago", status: "Stable" },
  { name: "Claims", cases: "516", backlog: "14", run: "5m ago", status: "Elevated" },
  { name: "Finance", cases: "388", backlog: "3", run: "9m ago", status: "Stable" },
  { name: "Policy", cases: "276", backlog: "9", run: "15m ago", status: "Review" },
  { name: "Support", cases: "202", backlog: "2", run: "21m ago", status: "Stable" },
  { name: "Audit", cases: "168", backlog: "5", run: "28m ago", status: "Review" },
];

const runtimeAttention = [
  "RUN-148 review required",
  "RUN-144 slow execution",
  "RUN-140 tool budget near limit",
  "RUN-136 retry completed",
  "RUN-131 case rebuild queued",
];

const backlogAttention = [
  "BATCH-08 pending reconciliation",
  "14 events waiting in Claims",
  "3 retries scheduled",
  "Policy queue requires review",
  "Audit batch not dispatched",
];

const recentActivity = [
  "Claims partition updated",
  "Tax facets refreshed",
  "Policy rebuild completed",
  "Finance backlog drained",
  "Audit run review closed",
];

const nextActions = [
  "Inspect Claims backlog",
  "Review Policy run history",
  "Check recent retries",
  "Open partition health",
  "Confirm Audit dispatch",
];

export function OverviewPage({
  activePartition,
  onActivatePartition,
}: {
  activePartition: string;
  onActivatePartition: (partitionName: string) => void;
}) {
  return (
    <section className="overview-page">
      <header className="overview-page-header">
        <div className="overview-page-copy">
          <h2>Overview</h2>
          <p>Partition health, queue pressure, and execution attention.</p>
        </div>
      </header>

      <section className="overview-status-strip">
        <article className="overview-status-card">
          <span>Partitions</span>
          <strong>12</strong>
          <small>stable</small>
        </article>
        <article className="overview-status-card">
          <span>Cases</span>
          <strong>2.4K</strong>
          <small>indexed</small>
        </article>
        <article className="overview-status-card">
          <span>Backlog</span>
          <strong>37</strong>
          <small>elevated</small>
        </article>
        <article className="overview-status-card">
          <span>Runs</span>
          <strong>148</strong>
          <small>healthy</small>
        </article>
        <article className="overview-status-card">
          <span>Review</span>
          <strong>6</strong>
          <small>required</small>
        </article>
      </section>

      <section className="overview-main-grid">
        <article className="skeleton-card overview-table-card">
          <div className="overview-panel-head">
            <h3>Partition List</h3>
            <button type="button" className="overview-inline-button">Create Partition</button>
          </div>
          <div className="overview-table-scroll">
            <div className="overview-table">
              <div className="overview-table-header">
                <span>Partition</span>
                <span>Cases</span>
                <span>Backlog</span>
                <span>Last run</span>
                <span>Status</span>
                <span>Active</span>
              </div>
              {partitionRows.map((row) => (
                <div key={row.name} className="overview-table-row">
                  <strong>{row.name}</strong>
                  <span>{row.cases}</span>
                  <span>{row.backlog}</span>
                  <span>{row.run}</span>
                  <span className={`overview-inline-status is-${row.status.toLowerCase()}`}>{row.status}</span>
                  <button
                    type="button"
                    className={`overview-activate-button${activePartition === row.name ? " is-active" : ""}`}
                    onClick={() => onActivatePartition(row.name)}
                  >
                    {activePartition === row.name ? "Active" : "Activate"}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </article>

        <div className="overview-side-stack">
          <article className="skeleton-card overview-attention-card">
            <div className="overview-panel-head">
              <h3>Runtime attention</h3>
            </div>
            <div className="overview-list-scroll">
              <ul className="overview-compact-list">
                {runtimeAttention.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </article>
          <article className="skeleton-card overview-attention-card">
            <div className="overview-panel-head">
              <h3>Backlog attention</h3>
            </div>
            <div className="overview-list-scroll">
              <ul className="overview-compact-list">
                {backlogAttention.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </article>
        </div>
      </section>

      <section className="overview-bottom-grid">
        <article className="skeleton-card overview-list-card">
          <div className="overview-panel-head">
            <h3>Recent activity</h3>
          </div>
          <div className="overview-list-scroll">
            <ul className="overview-compact-list">
              {recentActivity.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </article>
        <article className="skeleton-card overview-list-card">
          <div className="overview-panel-head">
            <h3>Next actions</h3>
          </div>
          <div className="overview-list-scroll">
            <ul className="overview-compact-list">
              {nextActions.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </article>
      </section>
    </section>
  );
}
