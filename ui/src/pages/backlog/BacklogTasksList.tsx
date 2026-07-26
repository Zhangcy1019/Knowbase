import type { ReactNode } from "react";

import type { PartitionTaskResponse } from "../../shared/api";
import { IconTraceLoop } from "../../shared/icons";

export type TaskStatus = "queued" | "running" | "completed" | "failed" | "cancelled";
export type TaskFilter = "all" | TaskStatus;

export const taskFilters: Array<[TaskFilter, string]> = [
  ["all", "All"],
  ["queued", "Queued"],
  ["running", "Running"],
  ["completed", "Done"],
  ["failed", "Failed"],
];

export function normalizeTaskStatus(status: string): TaskStatus {
  if (status === "queued" || status === "running" || status === "completed" || status === "failed" || status === "cancelled") {
    return status;
  }
  return "queued";
}

export function formatTaskTime(value: string | null) {
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

export function countTasks(tasks: PartitionTaskResponse[], status: TaskFilter) {
  return status === "all" ? tasks.length : tasks.filter((task) => normalizeTaskStatus(task.status) === status).length;
}

function TaskTitle({ children }: { children: ReactNode }) {
  return (
    <span className="backlog-task-title">
      <IconTraceLoop aria-hidden="true" />
      {children}
    </span>
  );
}

type BacklogTasksListProps = {
  activePartition: string | null;
  tasks: PartitionTaskResponse[];
  selectedTaskId: string;
  statusFilter: TaskFilter;
  loading: boolean;
  errorMessage: string;
  onSelectTask: (taskId: string) => void;
  onChangeFilter: (filter: TaskFilter) => void;
};

export function BacklogTasksList({
  activePartition,
  tasks,
  selectedTaskId,
  statusFilter,
  loading,
  errorMessage,
  onSelectTask,
  onChangeFilter,
}: BacklogTasksListProps) {
  const filteredTasks = statusFilter === "all"
    ? tasks
    : tasks.filter((task) => normalizeTaskStatus(task.status) === statusFilter);

  return (
    <article className="skeleton-card backlog-rail-card">
      <div className="backlog-panel-head">
        <div className="backlog-panel-heading">
          <span className="backlog-panel-mark"><IconTraceLoop aria-hidden="true" /></span>
          <h3>Tasks</h3>
        </div>
        {activePartition ? <code>{activePartition}</code> : null}
      </div>

      <div className="backlog-filter-strip">
        {taskFilters.map(([filter, label]) => (
          <button
            key={filter}
            type="button"
            className={`backlog-chip backlog-chip-button${statusFilter === filter ? " is-active" : ""}`}
            onClick={() => onChangeFilter(filter)}
          >
            {label} {countTasks(tasks, filter)}
          </button>
        ))}
      </div>

      <div className="backlog-list-scroll">
        <div className="backlog-list">
          {!activePartition ? <div className="backlog-empty-state">Select or create a partition first.</div> : null}
          {loading ? <div className="backlog-empty-state">Loading tasks...</div> : null}
          {!loading && errorMessage ? <div className="backlog-empty-state">{errorMessage}</div> : null}
          {!loading && activePartition && !errorMessage && filteredTasks.length === 0 ? (
            <div className="backlog-empty-state">No backlog tasks for the active partition.</div>
          ) : null}
          {filteredTasks.map((task) => {
            const status = normalizeTaskStatus(task.status);
            return (
              <div
                key={task.task_id}
                className={`backlog-row${task.task_id === selectedTaskId ? " is-active" : ""}`}
                role="button"
                tabIndex={0}
                onClick={() => onSelectTask(task.task_id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelectTask(task.task_id);
                  }
                }}
              >
                <div className="backlog-row-top">
                  <strong><TaskTitle>{task.task_id}</TaskTitle></strong>
                  <span className={`backlog-inline-status is-${status}`}>{status}</span>
                </div>
                <div className="backlog-row-meta">
                  <span>{task.kind}</span>
                  <span>{formatTaskTime(task.created_at)}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </article>
  );
}
