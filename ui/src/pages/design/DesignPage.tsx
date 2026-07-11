import "./design.css";

const palette = [
  { name: "Basalt", hex: "#1E2732", note: "Structure" },
  { name: "Slate", hex: "#556476", note: "Text" },
  { name: "Mist", hex: "#E9EEF2", note: "Background" },
  { name: "Chalk", hex: "#F7FAFC", note: "Surface" },
  { name: "Copper", hex: "#C67A2B", note: "Accent" },
  { name: "Signal Blue", hex: "#3B82A6", note: "Link" },
];

const shadows = [
  { name: "Soft Lift", value: "0 18px 48px rgba(34, 58, 84, 0.12)" },
  { name: "Panel Edge", value: "inset 0 1px 0 rgba(255, 255, 255, 0.54)" },
  { name: "Focused Depth", value: "0 10px 28px rgba(28, 49, 71, 0.22)" },
];

export function DesignPage() {
  return (
    <section className="design-page">
      <header className="design-page-header">
        <div className="design-page-copy">
          <h2>Design Language</h2>
          <p>A light card-based direction with small radii and restrained accent color.</p>
        </div>
        <div className="context-chip">
          <span>Route</span>
          <strong>/design</strong>
        </div>
      </header>

      <section className="page-grid-2">
        <article className="skeleton-card design-thesis-card">
          <span className="card-kicker">Direction</span>
          <h3>Quiet, light, structured</h3>
          <p>Soft background, clear cards, one restrained accent.</p>
          <div className="design-thesis-surface">
            <div className="design-thesis-grid" />
            <div className="design-thesis-panel">Cards / Text / Accent</div>
          </div>
        </article>

        <div className="page-stack">
          <article className="skeleton-card">
            <span className="card-kicker">Keywords</span>
            <h3>Quiet vocabulary</h3>
            <div className="design-keyword-row">
              <span>Quiet</span>
              <span>Ordered</span>
              <span>Light</span>
            </div>
          </article>
          <article className="skeleton-card">
            <span className="card-kicker">Rule</span>
            <h3>Color is limited</h3>
            <p>Most surfaces stay neutral. Accent appears only where action matters.</p>
          </article>
        </div>
      </section>

      <section className="page-stack">
        <header className="design-section-header">
          <h3>Color System</h3>
          <p>Six tokens.</p>
        </header>
        <div className="design-palette-grid">
          {palette.map((item) => (
            <article key={item.name} className="skeleton-card design-swatch-card">
              <div className="design-swatch" style={{ background: item.hex }} />
              <strong>{item.name}</strong>
              <code>{item.hex}</code>
              <p>{item.note}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="page-grid-2">
        <article className="skeleton-card">
          <span className="card-kicker">Type</span>
          <h3>Type roles</h3>
          <div className="design-type-stack">
            <div className="design-type-sample">
              <span className="design-type-label">Display</span>
              <p className="design-type-display">Run Ledger</p>
            </div>
            <div className="design-type-sample">
              <span className="design-type-label">Body</span>
              <p className="design-type-body">Body text stays plain, short, and readable.</p>
            </div>
            <div className="design-type-sample">
              <span className="design-type-label">Utility</span>
              <p className="design-type-utility">RUN-148 / BATCH-08 / CASE-2014</p>
            </div>
          </div>
        </article>

        <article className="skeleton-card">
          <span className="card-kicker">Spacing</span>
          <h3>Spacing</h3>
          <div className="design-spacing-scale">
            <div><strong>8</strong><span>Inline</span></div>
            <div><strong>14</strong><span>Controls</span></div>
            <div><strong>18</strong><span>Default</span></div>
            <div><strong>24</strong><span>Section</span></div>
            <div><strong>32</strong><span>Major</span></div>
          </div>
        </article>
      </section>

      <section className="page-stack">
        <header className="design-section-header">
          <h3>Cards and shadows</h3>
          <p>Small radius. Light edge. Soft depth.</p>
        </header>
        <div className="design-card-grid">
          <article className="skeleton-card design-demo-card">
            <span className="card-kicker">Default</span>
            <h4>Primary card</h4>
            <p>Main work surface.</p>
          </article>
          <article className="skeleton-card is-accent design-demo-card">
            <span className="card-kicker">Accent</span>
            <h4>Accent card</h4>
            <p>Guided focus.</p>
          </article>
          <article className="skeleton-card design-demo-card">
            <span className="card-kicker">Quiet</span>
            <h4>Secondary card</h4>
            <p>Supporting context.</p>
          </article>
        </div>
        <div className="design-shadow-grid">
          {shadows.map((shadow) => (
            <article key={shadow.name} className="skeleton-card design-shadow-card">
              <div className="design-shadow-sample" style={{ boxShadow: shadow.value }} />
              <strong>{shadow.name}</strong>
              <code>{shadow.value}</code>
            </article>
          ))}
        </div>
      </section>

      <section className="page-grid-3">
        <article className="skeleton-card">
          <span className="card-kicker">Status</span>
          <h4>Status</h4>
          <div className="design-status-row">
            <span className="design-status is-stable">Stable</span>
            <span className="design-status is-active">Running</span>
            <span className="design-status is-warning">Review</span>
          </div>
        </article>
        <article className="skeleton-card">
          <span className="card-kicker">Chips</span>
          <h4>Chips</h4>
          <div className="design-chip-row">
            <span className="design-chip">Tax</span>
            <span className="design-chip">Procedure</span>
            <span className="design-chip">Case Cluster</span>
          </div>
        </article>
        <article className="skeleton-card">
          <span className="card-kicker">Buttons</span>
          <h4>Buttons</h4>
          <div className="design-button-row">
            <button type="button" className="design-button is-primary">Drain backlog</button>
            <button type="button" className="design-button is-secondary">View details</button>
          </div>
        </article>
      </section>
    </section>
  );
}
