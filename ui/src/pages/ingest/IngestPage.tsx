import "./ingest.css";

const ingestSummary = [
  { label: "Queue", value: "14", note: "pending" },
  { label: "Accepted", value: "128", note: "today" },
  { label: "Rejected", value: "3", note: "today" },
];

const resultLines = [
  { label: "Status", value: "Ready to submit" },
  { label: "Partition", value: "Claims" },
  { label: "Case ID", value: "Pending" },
  { label: "Backlog", value: "Not created" },
];

export function IngestPage() {
  return (
    <section className="ingest-page">
      <header className="ingest-page-header">
        <div className="ingest-page-copy">
          <h2>Ingest</h2>
          <p>Paste one document, submit it, and review the returned result in the same workspace.</p>
        </div>
      </header>

      <section className="ingest-summary-strip">
        {ingestSummary.map((item) => (
          <article key={item.label} className="ingest-summary-card">
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <small>{item.note}</small>
          </article>
        ))}
      </section>

      <section className="ingest-workspace">
        <article className="skeleton-card ingest-editor-card">
          <div className="ingest-panel-head">
            <h3>Document Input</h3>
          </div>

          <div className="ingest-form-grid">
            <label className="ingest-field">
              <span>Partition</span>
              <input type="text" value="Claims" readOnly />
            </label>

            <label className="ingest-field">
              <span>Title</span>
              <input type="text" placeholder="Document title" />
            </label>

            <label className="ingest-field is-wide">
              <span>Source refs</span>
              <input type="text" placeholder="url, file path, external ref..." />
            </label>

            <label className="ingest-field is-wide">
              <span>Document content</span>
              <textarea
                rows={11}
                placeholder="Paste one document or case content here..."
              />
            </label>
          </div>

          <div className="ingest-actions-bar">
            <div className="ingest-actions">
              <button type="button" className="ingest-secondary-button">
                Clear
              </button>
              <button type="button" className="ingest-primary-button">
                Submit
              </button>
            </div>
          </div>
        </article>

        <article className="skeleton-card ingest-result-card">
          <div className="ingest-panel-head">
            <h3>Submit Result</h3>
          </div>

          <div className="ingest-result-state">
            <strong>No submission yet</strong>
            <p>Submit one document to review accepted status, generated case id, and returned processing details here.</p>
          </div>

          <div className="ingest-result-list">
            {resultLines.map((item) => (
              <div key={item.label} className="ingest-result-row">
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>
            ))}
          </div>

          <div className="ingest-result-log">
            <div className="ingest-result-log-head">
              <span>Response preview</span>
            </div>
            <pre>{`{
  "accepted": true,
  "processing_status": "queued",
  "case_id": "",
  "backlog_event_ids": []
}`}</pre>
          </div>
        </article>
      </section>
    </section>
  );
}
