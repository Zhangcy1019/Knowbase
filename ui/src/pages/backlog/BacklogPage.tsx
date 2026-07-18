import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import "./backlog.css";
import { IconBacklog, IconTraceDetail, IconTraceFocus, IconTraceList } from "../../shared/icons";
import {
  deleteBacklogEvent,
  drainBacklog,
  getBacklogEvent,
  listBacklogEvents,
  retryBacklogEvent,
  type EventRecordResponse,
  type MaintenanceActionResponse,
} from "../../shared/api";

function PanelMark({ children }: { children: ReactNode }) {
  return <span className="backlog-panel-mark">{children}</span>;
}

function formatTime(value: string | null) {
  if (!value) {
    return "--";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatDateTime(value: string | null) {
  if (!value) {
    return "--";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString([], {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function buildResourceRef(event: EventRecordResponse | null) {
  if (!event) {
    return "--";
  }
  if (!event.resource_type && !event.resource_id) {
    return "--";
  }
  return `${event.resource_type}:${event.resource_id}`;
}

function buildCounts(events: EventRecordResponse[]) {
  return events.reduce(
    (acc, event) => {
      acc.total += 1;
      if (event.status === "ready" || event.status === "recorded") {
        acc.ready += 1;
      }
      if (event.status === "failed") {
        acc.failed += 1;
      }
      if (event.status === "materialized") {
        acc.materialized += 1;
      }
      return acc;
    },
    { total: 0, ready: 0, failed: 0, materialized: 0 },
  );
}

function summarizeEventTypes(events: EventRecordResponse[]) {
  const counts = new Map<string, number>();
  events.forEach((event) => {
    counts.set(event.event_type, (counts.get(event.event_type) ?? 0) + 1);
  });
  return Array.from(counts.entries())
    .sort((left, right) => right[1] - left[1])
    .slice(0, 3);
}

export function BacklogPage({ activePartition }: { activePartition: string | null }) {
  const [events, setEvents] = useState<EventRecordResponse[]>([]);
  const [selectedEventId, setSelectedEventId] = useState("");
  const [selectedEvent, setSelectedEvent] = useState<EventRecordResponse | null>(null);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [actionPending, setActionPending] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [consoleMessage, setConsoleMessage] = useState("");
  const counts = useMemo(() => buildCounts(events), [events]);
  const eventTypeSummary = useMemo(() => summarizeEventTypes(events), [events]);

  useEffect(() => {
    let cancelled = false;
    if (!activePartition?.trim()) {
      setEvents([]);
      setSelectedEventId("");
      setSelectedEvent(null);
      setErrorMessage("");
      setConsoleMessage("");
      setLoadingEvents(false);
      return () => {
        cancelled = true;
      };
    }
    setLoadingEvents(true);
    setErrorMessage("");
    setConsoleMessage("");
    listBacklogEvents({ partition: activePartition })
      .then((items) => {
        if (cancelled) {
          return;
        }
        setEvents(items);
        setSelectedEventId((current) => {
          if (current && items.some((item) => item.event_id === current)) {
            return current;
          }
          return items[0]?.event_id ?? "";
        });
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        setEvents([]);
        setSelectedEventId("");
        setSelectedEvent(null);
        setErrorMessage(error instanceof Error ? error.message : "Failed to load backlog.");
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingEvents(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [activePartition]);

  useEffect(() => {
    let cancelled = false;
    if (!selectedEventId) {
      setSelectedEvent(null);
      setLoadingDetail(false);
      return () => {
        cancelled = true;
      };
    }
    setLoadingDetail(true);
    getBacklogEvent(selectedEventId)
      .then((event) => {
        if (!cancelled) {
          setSelectedEvent(event);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setSelectedEvent(null);
          setErrorMessage(error instanceof Error ? error.message : "Failed to load event detail.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingDetail(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedEventId]);

  async function reloadEvents(nextSelectedId?: string) {
    if (!activePartition?.trim()) {
      return;
    }
    const items = await listBacklogEvents({ partition: activePartition });
    setEvents(items);
    const fallbackId = nextSelectedId && items.some((item) => item.event_id === nextSelectedId)
      ? nextSelectedId
      : items[0]?.event_id ?? "";
    setSelectedEventId(fallbackId);
  }

  async function handleRetry() {
    if (!selectedEvent) {
      return;
    }
    setActionPending("retry");
    setErrorMessage("");
    try {
      const updated = await retryBacklogEvent(selectedEvent.event_id);
      setConsoleMessage(`Retried ${updated.event_id}.`);
      await reloadEvents(updated.event_id);
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to retry event.");
    } finally {
      setActionPending("");
    }
  }

  async function handleDelete() {
    if (!selectedEvent) {
      return;
    }
    setActionPending("delete");
    setErrorMessage("");
    try {
      await deleteBacklogEvent(selectedEvent.event_id);
      setConsoleMessage(`Deleted ${selectedEvent.event_id}.`);
      await reloadEvents();
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to delete event.");
    } finally {
      setActionPending("");
    }
  }

  async function handleDrain() {
    if (!activePartition?.trim()) {
      return;
    }
    setActionPending("drain");
    setErrorMessage("");
    try {
      const result = await drainBacklog(activePartition);
      setConsoleMessage(buildDrainMessage(result));
      await reloadEvents(selectedEventId);
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to drain backlog.");
    } finally {
      setActionPending("");
    }
  }

  const selectedResourceRef = buildResourceRef(selectedEvent);
  const lastRunAt = selectedEvent?.last_run_at ?? null;

  return (
    <section className="backlog-page">
      <header className="backlog-page-header">
        <div className="backlog-page-copy">
          <h2>Backlog</h2>
        </div>
      </header>

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
              <span>{activePartition || "No active partition"}</span>
            </div>
            <div className="backlog-mini-stats">
              <div>
                <span>Ready</span>
                <strong>{counts.ready}</strong>
              </div>
              <div>
                <span>Failed</span>
                <strong>{counts.failed}</strong>
              </div>
              <div>
                <span>Total</span>
                <strong>{counts.total}</strong>
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
              onClick={() => void handleDrain()}
              disabled={!activePartition || actionPending === "drain"}
            >
              {actionPending === "drain" ? "Draining..." : "Drain backlog"}
            </button>
            <button
              type="button"
              onClick={() => void handleRetry()}
              disabled={!selectedEvent || actionPending === "retry"}
            >
              {actionPending === "retry" ? "Retrying..." : "Retry failed"}
            </button>
          </div>
        </div>

        {consoleMessage ? <div className="backlog-console-note">{consoleMessage}</div> : null}
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
            <span className="backlog-chip is-active">{activePartition || "No active partition"}</span>
            <span className="backlog-chip">Ready {counts.ready}</span>
            <span className="backlog-chip">Failed {counts.failed}</span>
          </div>

          <div className="backlog-list-scroll">
            <div className="backlog-list">
              {!activePartition ? <div className="backlog-empty-state">Select or create a partition first.</div> : null}
              {loadingEvents ? <div className="backlog-empty-state">Loading backlog...</div> : null}
              {!loadingEvents && errorMessage ? <div className="backlog-empty-state">{errorMessage}</div> : null}
              {!loadingEvents && activePartition && !errorMessage && events.length === 0 ? (
                <div className="backlog-empty-state">No backlog events for the active partition.</div>
              ) : null}
              {events.map((row) => (
                <button
                  key={row.event_id}
                  type="button"
                  className={`backlog-row${row.event_id === selectedEventId ? " is-active" : ""}`}
                  onClick={() => setSelectedEventId(row.event_id)}
                >
                  <div className="backlog-row-top">
                    <strong>{row.partition || "--"}</strong>
                    <span className={`backlog-inline-status is-${row.status}`}>{row.status}</span>
                  </div>
                  <div className="backlog-row-meta">
                    <code>{row.event_id}</code>
                    <span>{row.event_type}</span>
                    <span>{row.resource_type || "--"}</span>
                    <span>#{row.attempt_count}</span>
                    <span>{formatTime(row.updated_at)}</span>
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
                <h3>{selectedEvent?.event_id || "No event"}</h3>
              </div>
              <code>{selectedEvent?.partition || activePartition || "No active partition"}</code>
            </div>

            <div className="backlog-summary-grid">
              <div className="backlog-summary-hero">
                <strong>{selectedEvent?.event_type || "Select an event to inspect detail."}</strong>
                <span>{selectedResourceRef}</span>
              </div>

              <div className="backlog-summary-stats">
                <div className="backlog-stat-card">
                  <span>Status</span>
                  <strong>{selectedEvent?.status || "--"}</strong>
                </div>
                <div className="backlog-stat-card">
                  <span>Disposition</span>
                  <strong>{selectedEvent?.disposition || "--"}</strong>
                </div>
                <div className="backlog-stat-card">
                  <span>Attempts</span>
                  <strong>{selectedEvent?.attempt_count ?? 0}</strong>
                </div>
                <div className="backlog-stat-card">
                  <span>Run</span>
                  <strong>{selectedEvent?.run_id || "--"}</strong>
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
              {!selectedEvent && !loadingDetail ? (
                <div className="backlog-empty-state">Select a backlog event to inspect detail.</div>
              ) : null}
              {loadingDetail ? <div className="backlog-empty-state">Loading detail...</div> : null}
              {selectedEvent ? (
                <div className="backlog-detail-stack">
                  <section className="backlog-detail-block">
                    <div className="backlog-detail-title">
                      <strong>Event</strong>
                      <code>{selectedEvent.event_id}</code>
                    </div>
                    <div className="backlog-detail-grid">
                      <span>Type</span>
                      <strong>{selectedEvent.event_type}</strong>
                      <span>Status</span>
                      <strong>{selectedEvent.status}</strong>
                      <span>Disposition</span>
                      <strong>{selectedEvent.disposition}</strong>
                      <span>Updated</span>
                      <strong>{formatDateTime(selectedEvent.updated_at)}</strong>
                      <span>Attempts</span>
                      <strong>{selectedEvent.attempt_count}</strong>
                    </div>
                  </section>

                  <section className="backlog-detail-block">
                    <div className="backlog-detail-title">
                      <strong>Resource</strong>
                      <code>{selectedResourceRef}</code>
                    </div>
                    <div className="backlog-detail-grid">
                      <span>Partition</span>
                      <strong>{selectedEvent.partition || "--"}</strong>
                      <span>Type</span>
                      <strong>{selectedEvent.resource_type || "--"}</strong>
                      <span>Id</span>
                      <strong>{selectedEvent.resource_id || "--"}</strong>
                    </div>
                  </section>

                  <section className="backlog-detail-block">
                    <div className="backlog-detail-title">
                      <strong>Run</strong>
                      <code>{selectedEvent.run_id || "Not materialized"}</code>
                    </div>
                    <div className="backlog-detail-grid">
                      <span>Run id</span>
                      <strong>{selectedEvent.run_id || "--"}</strong>
                      <span>Last run</span>
                      <strong>{formatDateTime(lastRunAt)}</strong>
                      <span>Error</span>
                      <strong>{selectedEvent.error_message || "No error recorded."}</strong>
                    </div>
                    <div className="backlog-detail-subsection">
                      <div className="backlog-detail-title">
                        <strong>Actions</strong>
                      </div>
                      <div className="backlog-detail-actions">
                        <button type="button" onClick={() => void handleRetry()} disabled={actionPending === "retry"}>
                          {actionPending === "retry" ? "Retrying..." : "Retry"}
                        </button>
                        <button type="button" onClick={() => void handleDelete()} disabled={actionPending === "delete"}>
                          {actionPending === "delete" ? "Deleting..." : "Delete"}
                        </button>
                        <button type="button" disabled={!selectedEvent.run_id}>
                          Open run
                        </button>
                      </div>
                    </div>
                  </section>
                </div>
              ) : null}
            </div>
          </article>
        </div>
      </section>
    </section>
  );
}

function buildDrainMessage(result: MaintenanceActionResponse) {
  const partition = typeof result.details.partition === "string" ? result.details.partition : "";
  const runId = typeof result.details.run_id === "string" ? result.details.run_id : "";
  const completed = typeof result.details.completed_count === "number" ? result.details.completed_count : 0;
  const failed = typeof result.details.failed_count === "number" ? result.details.failed_count : 0;
  return `${partition || "Partition"} drained: ${completed} completed, ${failed} failed${runId ? `, run ${runId}` : ""}.`;
}
