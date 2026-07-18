import type { ReactNode } from "react";

import "./backlog.css";
import { IconBacklog, IconTraceDetail, IconTraceFocus, IconTraceList } from "../../shared/icons";

type BacklogRow = {
  eventId: string;
  eventType: string;
  partition: string;
  status: "ready" | "failed" | "materialized" | "completed";
  disposition: "immediate" | "deferred";
  attempts: number;
  updatedAt: string;
  runId: string;
  error: string;
  resourceRef: string;
  changedField: string;
};

const backlogRows: BacklogRow[] = [
  {
    eventId: "evt_claims_1042",
    eventType: "case.updated",
    partition: "Claims",
    status: "ready",
    disposition: "immediate",
    attempts: 0,
    updatedAt: "09:24",
    runId: "",
    error: "",
    resourceRef: "case:claim-1042",
    changedField: "facets",
  },
  {
    eventId: "evt_tax_2091",
    eventType: "case.updated",
    partition: "Tax",
    status: "failed",
    disposition: "deferred",
    attempts: 2,
    updatedAt: "09:10",
    runId: "run_tax_144",
    error: "Planner returned invalid action payload.",
    resourceRef: "case:tax-2091",
    changedField: "semantic_profile",
  },
  {
    eventId: "evt_policy_332",
    eventType: "case.created",
    partition: "Policy",
    status: "materialized",
    disposition: "immediate",
    attempts: 1,
    updatedAt: "08:58",
    runId: "run_policy_077",
    error: "",
    resourceRef: "case:policy-332",
    changedField: "summary_text",
  },
  {
    eventId: "evt_finance_882",
    eventType: "case.updated",
    partition: "Finance",
    status: "completed",
    disposition: "deferred",
    attempts: 1,
    updatedAt: "08:31",
    runId: "run_fin_301",
    error: "",
    resourceRef: "case:finance-882",
    changedField: "metadata",
  },
];

const selectedEvent = backlogRows[1];

function PanelMark({ children }: { children: ReactNode }) {
  return <span className="backlog-panel-mark">{children}</span>;
}

export function BacklogPage() {
  return (
    <section className="backlog-page">
      <header className="backlog-page-header">
        <div className="backlog-page-copy">
          <h2>Backlog</h2>
        </div>
        <div className="backlog-page-status">
          <span className="backlog-page-pill">17</span>
          <span className="backlog-page-pill is-accent">3 failed</span>
        </div>
      </header>

      <section className="backlog-status-strip">
        <article className="backlog-status-card">
          <span>Ready</span>
          <strong>9</strong>
        </article>
        <article className="backlog-status-card">
          <span>Materialized</span>
          <strong>4</strong>
        </article>
        <article className="backlog-status-card">
          <span>Failed</span>
          <strong>3</strong>
        </article>
        <article className="backlog-status-card is-accent">
          <span>Drained today</span>
          <strong>28</strong>
        </article>
      </section>

      <section className="skeleton-card backlog-control-card">
        <div className="backlog-panel-head">
          <div className="backlog-panel-heading">
            <PanelMark>
              <IconBacklog />
            </PanelMark>
            <h3>Drain Console</h3>
          </div>
        </div>

        <div className="backlog-control-grid">
          <div className="backlog-control-section">
            <div className="backlog-side-title">
              <strong>Partition</strong>
              <span>Claims</span>
            </div>
            <div className="backlog-mini-stats">
              <div>
                <span>Ready</span>
                <strong>5</strong>
              </div>
              <div>
                <span>Failed</span>
                <strong>2</strong>
              </div>
              <div>
                <span>Last run</span>
                <strong>08:58</strong>
              </div>
            </div>
          </div>

          <div className="backlog-control-section">
            <div className="backlog-side-title">
              <strong>Next drain</strong>
              <span>6 events</span>
            </div>
            <ul className="backlog-compact-list">
              <li>4 case.updated</li>
              <li>1 case.created</li>
              <li>1 backlog.requested</li>
            </ul>
          </div>

          <div className="backlog-control-actions">
            <button type="button" className="is-primary">Drain backlog</button>
            <button type="button">Retry failed</button>
          </div>
        </div>
      </section>

      <section className="backlog-workbench">
        <article className="skeleton-card backlog-rail-card">
          <div className="backlog-panel-head">
            <div className="backlog-panel-heading">
              <PanelMark>
                <IconTraceList />
              </PanelMark>
              <h3>Events</h3>
            </div>
          </div>

          <div className="backlog-filter-strip">
            <span className="backlog-chip is-active">Claims</span>
            <span className="backlog-chip">Ready</span>
            <span className="backlog-chip">Failed 3</span>
          </div>

          <div className="backlog-list-scroll">
            <div className="backlog-list">
              {backlogRows.map((row, index) => (
                <button
                  key={row.eventId}
                  type="button"
                  className={`backlog-row${index === 1 ? " is-active" : ""}`}
                >
                  <div className="backlog-row-top">
                    <strong>{row.partition}</strong>
                    <span className={`backlog-inline-status is-${row.status}`}>{row.status}</span>
                  </div>
                  <div className="backlog-row-meta">
                    <code>{row.eventId}</code>
                    <span>{row.eventType}</span>
                    <span>{row.changedField}</span>
                    <span>#{row.attempts}</span>
                    <span>{row.updatedAt}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </article>

        <div className="backlog-center-stack">
          <article className="skeleton-card backlog-summary-card">
            <div className="backlog-panel-head">
              <div className="backlog-panel-heading">
                <PanelMark>
                  <IconTraceFocus />
                </PanelMark>
                <h3>{selectedEvent.eventId}</h3>
              </div>
              <code>{selectedEvent.partition}</code>
            </div>

            <div className="backlog-summary-grid">
              <div className="backlog-summary-hero">
                <strong>{selectedEvent.eventType}</strong>
                <span>{selectedEvent.resourceRef}</span>
              </div>

              <div className="backlog-summary-stats">
                <div className="backlog-stat-card">
                  <span>Status</span>
                  <strong>{selectedEvent.status}</strong>
                </div>
                <div className="backlog-stat-card">
                  <span>Disposition</span>
                  <strong>{selectedEvent.disposition}</strong>
                </div>
                <div className="backlog-stat-card">
                  <span>Attempts</span>
                  <strong>{selectedEvent.attempts}</strong>
                </div>
                <div className="backlog-stat-card">
                  <span>Run</span>
                  <strong>{selectedEvent.runId || "--"}</strong>
                </div>
              </div>
            </div>
          </article>

          <article className="skeleton-card backlog-detail-card">
            <div className="backlog-panel-head">
              <div className="backlog-panel-heading">
                <PanelMark>
                  <IconTraceDetail />
                </PanelMark>
                <h3>Detail</h3>
              </div>
            </div>

            <div className="backlog-detail-scroll">
              <div className="backlog-detail-stack">
                <section className="backlog-detail-block">
                  <div className="backlog-detail-title">
                    <strong>Resource</strong>
                    <code>{selectedEvent.resourceRef}</code>
                  </div>
                  <div className="backlog-detail-grid">
                    <span>Event</span>
                    <strong>{selectedEvent.eventId}</strong>
                    <span>Changed</span>
                    <strong>{selectedEvent.changedField}</strong>
                    <span>Updated</span>
                    <strong>{selectedEvent.updatedAt}</strong>
                  </div>
                </section>

                <section className="backlog-detail-block">
                  <div className="backlog-detail-title">
                    <strong>Failure</strong>
                    <span>{selectedEvent.error || "No error recorded."}</span>
                  </div>
                </section>

                <section className="backlog-detail-block">
                  <div className="backlog-detail-title">
                    <strong>Actions</strong>
                  </div>
                  <div className="backlog-detail-actions">
                    <button type="button">Retry</button>
                    <button type="button">Delete</button>
                    <button type="button">Open run</button>
                  </div>
                </section>
              </div>
            </div>
          </article>
        </div>
      </section>
    </section>
  );
}
