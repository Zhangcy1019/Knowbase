import type { MouseEvent, ReactNode, RefObject } from "react";

import { ConfirmDeletePopover } from "../../shared/component/confirm";
import { IconDelete, IconSend, IconTraceList } from "../../shared/icons";
import type { EventRecordResponse } from "../../shared/api";

type BacklogEventsListProps = {
  activePartition: string | null;
  counts: {
    total: number;
    pending: number;
    failed: number;
  };
  statusFilter: "all" | "pending" | "failed";
  filteredEvents: EventRecordResponse[];
  selectedEventId: string;
  loadingEvents: boolean;
  errorMessage: string;
  deleteErrorMessage: string;
  deleteConfirmEventId: string;
  deletingEventId: string;
  deletePopoverPosition: { top: number; left: number } | null;
  deletePopoverRef: RefObject<HTMLDivElement | null>;
  onSelectEvent: (eventId: string) => void;
  onChangeStatusFilter: (filter: "all" | "pending" | "failed") => void;
  onToggleDelete: (eventId: string, event: MouseEvent<HTMLButtonElement>) => void;
  onCancelDelete: () => void;
  onConfirmDelete: (eventId: string) => void;
  formatTime: (value: string | null) => string;
  onOpenDrainConfirm: () => void;
  draining: boolean;
  consoleMessage: string;
};

function PanelMark({ children }: { children: ReactNode }) {
  return <span className="backlog-panel-mark">{children}</span>;
}

export function BacklogEventsList({
  activePartition,
  counts,
  statusFilter,
  filteredEvents,
  selectedEventId,
  loadingEvents,
  errorMessage,
  deleteErrorMessage,
  deleteConfirmEventId,
  deletingEventId,
  deletePopoverPosition,
  deletePopoverRef,
  onSelectEvent,
  onChangeStatusFilter,
  onToggleDelete,
  onCancelDelete,
  onConfirmDelete,
  formatTime,
  onOpenDrainConfirm,
  draining,
  consoleMessage,
}: BacklogEventsListProps) {
  return (
    <article className="skeleton-card backlog-rail-card">
      <div className="backlog-panel-head">
        <div className="backlog-panel-heading">
          <PanelMark>
            <IconTraceList />
          </PanelMark>
          <h3>Events</h3>
        </div>
        <div className="backlog-panel-actions">
          {activePartition ? <code>{activePartition}</code> : null}
          <button
            type="button"
            className="backlog-drain-button"
            onClick={onOpenDrainConfirm}
            disabled={!activePartition || draining}
            data-backlog-drain-trigger="true"
          >
            <IconSend />
            <span>{draining ? "Draining" : "Drain pending"}</span>
          </button>
          {consoleMessage ? <span className="backlog-action-note" aria-live="polite">{consoleMessage}</span> : null}
        </div>
      </div>

      <div className="backlog-filter-strip">
        <button
          type="button"
          className={`backlog-chip backlog-chip-button${statusFilter === "all" ? " is-active" : ""}`}
          onClick={() => onChangeStatusFilter("all")}
        >
          All {counts.total}
        </button>
        <button
          type="button"
          className={`backlog-chip backlog-chip-button${statusFilter === "pending" ? " is-active" : ""}`}
          onClick={() => onChangeStatusFilter("pending")}
        >
          Pending {counts.pending}
        </button>
        <button
          type="button"
          className={`backlog-chip backlog-chip-button${statusFilter === "failed" ? " is-active" : ""}`}
          onClick={() => onChangeStatusFilter("failed")}
        >
          Failed {counts.failed}
        </button>
      </div>

      <div className="backlog-list-scroll">
        <div className="backlog-list">
          {!activePartition ? <div className="backlog-empty-state">Select or create a partition first.</div> : null}
          {loadingEvents ? <div className="backlog-empty-state">Loading backlog...</div> : null}
          {!loadingEvents && errorMessage ? <div className="backlog-empty-state">{errorMessage}</div> : null}
          {!loadingEvents && activePartition && !errorMessage && filteredEvents.length === 0 ? (
            <div className="backlog-empty-state">No backlog events for the active partition.</div>
          ) : null}
          {filteredEvents.map((row) => (
            <div
              key={row.event_id}
              className={`backlog-row${row.event_id === selectedEventId ? " is-active" : ""}`}
              role="button"
              tabIndex={0}
              onClick={() => onSelectEvent(row.event_id)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelectEvent(row.event_id);
                }
              }}
            >
              <div className="backlog-row-top">
                <strong>{row.event_type}</strong>
                <div className="backlog-row-top-right">
                  <div className="backlog-list-delete-wrap">
                    <button
                      type="button"
                      className="backlog-list-delete"
                      onClick={(event) => onToggleDelete(row.event_id, event)}
                      disabled={deletingEventId === row.event_id}
                      data-backlog-delete-trigger={row.event_id}
                      aria-label={`Delete ${row.event_id}`}
                      title="Delete"
                    >
                      <IconDelete />
                    </button>
                    {deleteConfirmEventId === row.event_id && deletePopoverPosition ? (
                      <ConfirmDeletePopover
                        ref={deletePopoverRef}
                        className="backlog-delete-popover"
                        style={{
                          top: deletePopoverPosition.top,
                          left: deletePopoverPosition.left,
                          transform: "translateY(-100%)",
                        }}
                        title={`Delete ${row.event_id}?`}
                        description="This will remove the backlog event."
                        errorMessage={deleteErrorMessage}
                        pending={deletingEventId === row.event_id}
                        onCancel={onCancelDelete}
                        onConfirm={() => onConfirmDelete(row.event_id)}
                      />
                    ) : null}
                  </div>
                </div>
              </div>
              <div className="backlog-row-meta">
                <span>{row.partition || "--"}</span>
                <span>{row.resource_type || "--"}</span>
                <span>Queued at {formatTime(row.updated_at)}</span>
                <code>{row.event_id}</code>
              </div>
            </div>
          ))}
        </div>
      </div>
    </article>
  );
}
