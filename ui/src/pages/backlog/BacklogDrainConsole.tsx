import type { ReactNode } from "react";

import { IconBacklog, IconSend } from "../../shared/icons";

type BacklogCounts = {
  total: number;
  pending: number;
  failed: number;
  completed: number;
};

type BacklogDrainConsoleProps = {
  activePartition: string | null;
  counts: BacklogCounts;
  eventTypeSummary: Array<[string, number]>;
  actionPending: string;
  consoleMessage: string;
  onDrain: () => void;
};

function PanelMark({ children }: { children: ReactNode }) {
  return <span className="backlog-panel-mark">{children}</span>;
}

export function BacklogDrainConsole({
  activePartition,
  counts,
  eventTypeSummary,
  actionPending,
  consoleMessage,
  onDrain,
}: BacklogDrainConsoleProps) {
  return (
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
            <strong>Status</strong>
            <span>{counts.total} events</span>
          </div>
          <div className="backlog-mini-stats">
            <div>
              <span>Pending</span>
              <strong>{counts.pending}</strong>
            </div>
            <div>
              <span>Failed</span>
              <strong>{counts.failed}</strong>
            </div>
            <div>
              <span>Done</span>
              <strong>{counts.completed}</strong>
            </div>
          </div>
        </div>

        <div className="backlog-control-section">
          <div className="backlog-side-title">
            <strong>Next drain</strong>
            <span>{counts.total} events</span>
          </div>
          <ul className="backlog-compact-list">
            {eventTypeSummary.length === 0 ? <li>No queued events</li> : null}
            {eventTypeSummary.map(([eventType, count]) => (
              <li key={eventType}>{count} {eventType}</li>
            ))}
          </ul>
        </div>

        <div className="backlog-control-actions">
          <button
            type="button"
            className="is-primary"
            onClick={onDrain}
            disabled={!activePartition || actionPending === "drain"}
          >
            <IconSend />
            <span>{actionPending === "drain" ? "Draining" : "Drain"}</span>
          </button>
        </div>
      </div>

      {consoleMessage ? <div className="backlog-console-note">{consoleMessage}</div> : null}
    </section>
  );
}
