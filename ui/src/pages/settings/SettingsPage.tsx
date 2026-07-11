import "./settings.css";

export function SettingsPage() {
  return (
    <section className="settings-page">
      <header className="settings-page-header">
        <div className="settings-page-copy">
          <h2>Settings</h2>
        </div>
      </header>

      <section className="page-grid-3">
        <article className="skeleton-card">
          <span className="card-kicker">Environment</span>
          <h3>Frontend Runtime Mode</h3>
          <p>Reserve this card for local, integrated, and development mode switches.</p>
          <div className="skeleton-lines">
            <span style={{ width: "72%" }} />
            <span style={{ width: "58%" }} />
          </div>
        </article>
        <article className="skeleton-card">
          <span className="card-kicker">Policy</span>
          <h3>Execution Guardrails</h3>
          <p>Request limits, action allowlists, and review gates can hang off this panel.</p>
          <div className="skeleton-lines">
            <span style={{ width: "84%" }} />
            <span style={{ width: "61%" }} />
          </div>
        </article>
        <article className="skeleton-card is-accent">
          <span className="card-kicker">Diagnostics</span>
          <h3>System Connections</h3>
          <p>Backend health, config snapshot, and integration checks belong here.</p>
          <div className="skeleton-lines">
            <span style={{ width: "76%" }} />
            <span style={{ width: "54%" }} />
          </div>
        </article>
      </section>
    </section>
  );
}
