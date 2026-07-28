import type { ReactNode } from "react";
import { IconTraceDetail } from "../../shared/icons";
import type { EventRecordResponse } from "../../shared/api";

type BacklogDetailPanelProps = {
  selectedEvent: EventRecordResponse | null;
  selectedResourceRef: string;
  lastRunAt: string | null;
  loadingDetail: boolean;
  actionPending: string;
  onRequeue: () => void;
  formatDateTime: (value: string | null) => string;
};

function PanelMark({ children }: { children: ReactNode }) {
  return <span className="backlog-panel-mark">{children}</span>;
}

export function BacklogDetailPanel({
  selectedEvent,
  selectedResourceRef,
  lastRunAt,
  loadingDetail,
  actionPending,
  onRequeue,
  formatDateTime,
}: BacklogDetailPanelProps) {
  return (
    <article className="skeleton-card backlog-detail-card backlog-detail-card-single">
      <div className="backlog-panel-head">
        <div className="backlog-panel-heading">
          <PanelMark>
            <IconTraceDetail />
          </PanelMark>
          <h3>{selectedEvent?.event_id || "Detail"}</h3>
        </div>
        {selectedEvent?.partition ? <code>{selectedEvent.partition}</code> : null}
      </div>

      <div className="backlog-detail-scroll">
        {!selectedEvent && !loadingDetail ? (
          <div className="backlog-empty-state">Select a backlog event to inspect detail.</div>
        ) : null}
        {loadingDetail ? <div className="backlog-empty-state">Loading detail...</div> : null}
        {selectedEvent ? (
          <div className="backlog-detail-stack">
            <section className="backlog-summary-hero backlog-detail-hero">
              <strong>{selectedEvent.event_type}</strong>
              <span>{selectedResourceRef}</span>
            </section>

            <div className="backlog-summary-stats backlog-detail-stats">
              <div className="backlog-stat-card">
                <span>Status</span>
                <strong>{selectedEvent.status || "--"}</strong>
              </div>
              <div className="backlog-stat-card">
                <span>Attempts</span>
                <strong>{selectedEvent.attempt_count ?? 0}</strong>
              </div>
              <div className="backlog-stat-card">
                <span>Run</span>
                <strong>{selectedEvent.run_id || "--"}</strong>
              </div>
            </div>

            <section className="backlog-detail-block">
              <div className="backlog-detail-title">
                <strong>Event</strong>
                <code>{selectedEvent.event_id}</code>
              </div>
              <div className="backlog-detail-grid">
                <span>Updated</span>
                <strong>{formatDateTime(selectedEvent.updated_at)}</strong>
                <span>Partition</span>
                <strong>{selectedEvent.partition || "--"}</strong>
                <span>Resource type</span>
                <strong>{selectedEvent.resource_type || "--"}</strong>
                <span>Resource id</span>
                <strong>{selectedEvent.resource_id || "--"}</strong>
              </div>
            </section>

            <section className="backlog-detail-block">
              <div className="backlog-detail-title">
                <strong>Run</strong>
                <code>{selectedEvent.run_id || "Not materialized"}</code>
              </div>
              <div className="backlog-detail-grid">
                <span>Last run</span>
                <strong>{formatDateTime(lastRunAt)}</strong>
                <span>Error</span>
                <strong>{selectedEvent.error_message || "No error recorded."}</strong>
              </div>
              <div className="backlog-detail-actions">
                <button
                  type="button"
                  onClick={onRequeue}
                  disabled={actionPending === "requeue"}
                >
                  {actionPending === "requeue" ? "Requeueing..." : "Requeue"}
                </button>
                {selectedEvent.run_id ? (
                  <a
                    className="backlog-detail-button"
                    href={`/runs?run_id=${encodeURIComponent(selectedEvent.run_id)}`}
                  >
                    Open run
                  </a>
                ) : (
                  <span className="backlog-detail-button is-disabled">Open run</span>
                )}
              </div>
            </section>
          </div>
        ) : null}
      </div>
    </article>
  );
}
