import type { MouseEvent, ReactNode, RefObject } from "react";

import { ConfirmDeletePopover } from "../../shared/component/confirm";
import { IconDelete, IconTraceList } from "../../shared/icons";
import type { RuntimeRunSummary } from "../../shared/api";

export type RunsStatusFilter = "all" | "review" | "completed" | "failed" | "running";

type RunsListPanelProps = {
  activePartition: string | null;
  runs: RuntimeRunSummary[];
  selectedRunId: string;
  loadingRuns: boolean;
  errorMessage: string;
  counts: Record<RunsStatusFilter, number>;
  statusFilter: RunsStatusFilter;
  deleteErrorMessage: string;
  deleteConfirmRunId: string;
  deletingRunId: string;
  deletePopoverPosition: { top: number; left: number } | null;
  deletePopoverRef: RefObject<HTMLDivElement | null>;
  onSelectRun: (runId: string) => void;
  onChangeStatusFilter: (filter: RunsStatusFilter) => void;
  onToggleDelete: (runId: string, event: MouseEvent<HTMLButtonElement>) => void;
  onCancelDelete: () => void;
  onConfirmDelete: (runId: string) => void;
  formatTime: (value: string | null) => string;
  formatStatus: (status: string, requiresReview: boolean) => string;
};

function PanelMark({ children }: { children: ReactNode }) {
  return <span className="runs-panel-mark">{children}</span>;
}

export function RunsListPanel({
  activePartition,
  runs,
  selectedRunId,
  loadingRuns,
  errorMessage,
  counts,
  statusFilter,
  deleteErrorMessage,
  deleteConfirmRunId,
  deletingRunId,
  deletePopoverPosition,
  deletePopoverRef,
  onSelectRun,
  onChangeStatusFilter,
  onToggleDelete,
  onCancelDelete,
  onConfirmDelete,
  formatTime,
  formatStatus,
}: RunsListPanelProps) {
  return (
    <article className="skeleton-card runs-rail-card">
      <div className="runs-panel-head">
        <div className="runs-panel-heading">
          <PanelMark>
            <IconTraceList />
          </PanelMark>
          <h3>List</h3>
        </div>
        <code>{activePartition || "No active partition"}</code>
      </div>

      <div className="runs-filter-strip">
        <button
          type="button"
          className={`runs-chip runs-chip-button${statusFilter === "all" ? " is-active" : ""}`}
          onClick={() => onChangeStatusFilter("all")}
        >
          All {counts.all}
        </button>
        <button
          type="button"
          className={`runs-chip runs-chip-button${statusFilter === "running" ? " is-active" : ""}`}
          onClick={() => onChangeStatusFilter("running")}
        >
          Running {counts.running}
        </button>
        <button
          type="button"
          className={`runs-chip runs-chip-button${statusFilter === "review" ? " is-active" : ""}`}
          onClick={() => onChangeStatusFilter("review")}
        >
          Review {counts.review}
        </button>
        <button
          type="button"
          className={`runs-chip runs-chip-button${statusFilter === "completed" ? " is-active" : ""}`}
          onClick={() => onChangeStatusFilter("completed")}
        >
          Done {counts.completed}
        </button>
        <button
          type="button"
          className={`runs-chip runs-chip-button${statusFilter === "failed" ? " is-active" : ""}`}
          onClick={() => onChangeStatusFilter("failed")}
        >
          Failed {counts.failed}
        </button>
      </div>

      <div className="runs-list-scroll">
        <div className="runs-list">
          {!activePartition ? <div className="runs-empty-state">Select or create a partition first.</div> : null}
          {loadingRuns ? <div className="runs-empty-state">Loading runs...</div> : null}
          {!loadingRuns && errorMessage ? <div className="runs-empty-state">{errorMessage}</div> : null}
          {!activePartition ? null : !loadingRuns && !errorMessage && runs.length === 0 ? (
            <div className="runs-empty-state">No runs for the active partition.</div>
          ) : null}
          {runs.map((run) => (
            <div
              key={run.run_id}
              className={`runs-row${run.run_id === selectedRunId ? " is-active" : ""}`}
              role="button"
              tabIndex={0}
              onClick={() => onSelectRun(run.run_id)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelectRun(run.run_id);
                }
              }}
            >
              <div className="runs-row-top">
                <strong>{run.run_id}</strong>
                <span className={`runs-inline-status is-${formatStatus(run.status, run.requires_review)}`}>
                  {formatStatus(run.status, run.requires_review)}
                </span>
              </div>
              <div className="runs-row-meta">
                <div className="runs-row-meta-copy">
                  <span>{formatTime(run.created_at)}</span>
                </div>
                <div className="runs-list-delete-wrap">
                  <button
                    type="button"
                    className="runs-list-delete"
                    onClick={(event) => onToggleDelete(run.run_id, event)}
                    disabled={deletingRunId === run.run_id}
                    data-runs-delete-trigger={run.run_id}
                    aria-label={`Delete ${run.run_id}`}
                    title="Delete"
                  >
                    <IconDelete />
                  </button>
                  {deleteConfirmRunId === run.run_id && deletePopoverPosition ? (
                    <ConfirmDeletePopover
                      ref={deletePopoverRef}
                      className="runs-delete-popover"
                      style={{
                        top: deletePopoverPosition.top,
                        left: deletePopoverPosition.left,
                        transform: "translateY(-100%)",
                      }}
                      title={`Delete ${run.run_id}?`}
                      description="This will remove the runtime run and its trace."
                      errorMessage={deleteErrorMessage}
                      pending={deletingRunId === run.run_id}
                      onCancel={onCancelDelete}
                      onConfirm={() => onConfirmDelete(run.run_id)}
                    />
                  ) : null}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </article>
  );
}
