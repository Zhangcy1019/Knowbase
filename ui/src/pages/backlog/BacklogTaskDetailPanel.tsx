import type { ReactNode } from "react";

import type { PartitionTaskResponse } from "../../shared/api";
import { IconTraceLoop } from "../../shared/icons";

import { formatTaskTime } from "./BacklogTasksList";

function TaskTitle({ children }: { children: ReactNode }) {
  return (
    <span className="backlog-task-title">
      <IconTraceLoop aria-hidden="true" />
      {children}
    </span>
  );
}

type BacklogTaskDetailPanelProps = {
  task: PartitionTaskResponse | null;
};

export function BacklogTaskDetailPanel({ task }: BacklogTaskDetailPanelProps) {
  return (
    <article className="skeleton-card backlog-detail-card backlog-detail-card-single">
      <div className="backlog-panel-head">
        <div className="backlog-panel-heading">
          <span className="backlog-panel-mark"><IconTraceLoop aria-hidden="true" /></span>
          <h3><TaskTitle>{task?.task_id || "Task detail"}</TaskTitle></h3>
        </div>
        {task?.partition ? <code>{task.partition}</code> : null}
      </div>
      <div className="backlog-detail-scroll">
        {task ? (
          <div className="backlog-detail-stack">
            <section className="backlog-summary-hero backlog-detail-hero">
              <strong><TaskTitle>{task.kind}</TaskTitle></strong>
              <span>{task.task_id}</span>
            </section>
            <div className="backlog-summary-stats backlog-detail-stats">
              <div className="backlog-stat-card">
                <span>Status</span>
                <strong>{task.status}</strong>
              </div>
              <div className="backlog-stat-card">
                <span>Created</span>
                <strong>{formatTaskTime(task.created_at)}</strong>
              </div>
              <div className="backlog-stat-card">
                <span>Attempts</span>
                <strong>{task.attempt_count}</strong>
              </div>
            </div>
            <section className="backlog-detail-block">
              <div className="backlog-detail-title">
                <strong><TaskTitle>Task</TaskTitle></strong>
                <code>{task.task_id}</code>
              </div>
              <div className="backlog-detail-grid">
                <span>Kind</span>
                <strong>{task.kind}</strong>
                <span>Partition</span>
                <strong>{task.partition}</strong>
                <span>Started</span>
                <strong>{formatTaskTime(task.started_at)}</strong>
                <span>Finished</span>
                <strong>{formatTaskTime(task.finished_at)}</strong>
                {task.error_message ? (
                  <>
                    <span>Error</span>
                    <strong>{task.error_message}</strong>
                  </>
                ) : null}
              </div>
            </section>
          </div>
        ) : (
          <div className="backlog-empty-state">Select a task to inspect detail.</div>
        )}
      </div>
    </article>
  );
}
