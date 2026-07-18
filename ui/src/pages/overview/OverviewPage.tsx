import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import "./overview.css";
import { IconBacklog, IconOverview, IconPartition, IconRuns, IconTraceList } from "../../shared/icons";
import {
  listBacklogEvents,
  listPartitionCases,
  listPartitions,
  listRuntimeRuns,
  type EventRecordResponse,
  type PartitionDocument,
  type RuntimeRunSummary,
} from "../../shared/api";

type OverviewPartitionRow = {
  name: string;
  cases: number;
  backlog: number;
  runAt: string | null;
  status: "stable" | "elevated" | "review";
};

type OverviewRecentChange = {
  id: string;
  label: string;
  timestamp: string | null;
};

function PanelMark({ children }: { children: ReactNode }) {
  return <span className="overview-panel-mark">{children}</span>;
}

function formatRelativeTime(value: string | null) {
  if (!value) {
    return "--";
  }
  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) {
    return "--";
  }
  const diffMinutes = Math.max(0, Math.round((Date.now() - timestamp) / 60000));
  if (diffMinutes < 1) {
    return "now";
  }
  if (diffMinutes < 60) {
    return `${diffMinutes}m ago`;
  }
  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }
  const diffDays = Math.round(diffHours / 24);
  return `${diffDays}d ago`;
}

function normalizePartitionStatus(
  partition: PartitionDocument,
  backlogCount: number,
  runs: RuntimeRunSummary[],
): OverviewPartitionRow["status"] {
  if (runs.some((item) => item.requires_review)) {
    return "review";
  }
  if (partition.status !== "active" || backlogCount >= 10) {
    return "elevated";
  }
  return "stable";
}

function buildRecentChanges(events: EventRecordResponse[], runs: RuntimeRunSummary[]): OverviewRecentChange[] {
  const runChanges = runs.map((run) => ({
    id: `run:${run.run_id}`,
    label: `${run.partition} run ${run.status || "updated"}`,
    timestamp: run.updated_at || run.finished_at || run.created_at,
  }));
  const eventChanges = events.map((event) => ({
    id: `event:${event.event_id}`,
    label: `${event.partition} backlog ${event.status || event.event_type}`,
    timestamp: event.updated_at || event.last_run_at || event.created_at || event.occurred_at,
  }));
  return [...runChanges, ...eventChanges]
    .sort((left, right) => {
      const leftTime = left.timestamp ? new Date(left.timestamp).getTime() : 0;
      const rightTime = right.timestamp ? new Date(right.timestamp).getTime() : 0;
      return rightTime - leftTime;
    })
    .slice(0, 6);
}

export function OverviewPage({
  activePartition,
  onActivatePartition,
}: {
  activePartition: string | null;
  onActivatePartition: (partitionName: string | null) => void;
}) {
  const [partitionRows, setPartitionRows] = useState<OverviewPartitionRow[]>([]);
  const [backlogEvents, setBacklogEvents] = useState<EventRecordResponse[]>([]);
  const [runs, setRuns] = useState<RuntimeRunSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErrorMessage("");
    Promise.all([listPartitions(), listBacklogEvents({}), listRuntimeRuns("")])
      .then(async ([partitions, events, runtimeRuns]) => {
        const rowPayload = await Promise.all(
          partitions.map(async (partition) => {
            const [cases, partitionRuns, partitionEvents] = await Promise.all([
              listPartitionCases(partition.partition_name),
              Promise.resolve(runtimeRuns.filter((item) => item.partition === partition.partition_name)),
              Promise.resolve(events.filter((item) => item.partition === partition.partition_name)),
            ]);
            const lastRunAt = partitionRuns
              .map((item) => item.updated_at || item.finished_at || item.created_at)
              .filter((item): item is string => Boolean(item))
              .sort((left, right) => new Date(right).getTime() - new Date(left).getTime())[0] ?? null;
            return {
              name: partition.partition_name,
              cases: cases.length,
              backlog: partitionEvents.length,
              runAt: lastRunAt,
              status: normalizePartitionStatus(partition, partitionEvents.length, partitionRuns),
            } satisfies OverviewPartitionRow;
          }),
        );
        rowPayload.sort((left, right) => left.name.localeCompare(right.name));
        if (cancelled) {
          return;
        }
        setPartitionRows(rowPayload);
        setBacklogEvents(events);
        setRuns(runtimeRuns);
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        setPartitionRows([]);
        setBacklogEvents([]);
        setRuns([]);
        setErrorMessage(error instanceof Error ? error.message : "Failed to load overview.");
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const recentChanges = useMemo(() => buildRecentChanges(backlogEvents, runs), [backlogEvents, runs]);
  const reviewCount = runs.filter((item) => item.requires_review).length;
  const readyBacklogCount = backlogEvents.filter((item) => item.status === "ready").length;
  const activePartitionCount = partitionRows.filter((item) => item.status === "stable").length;
  const totalCases = partitionRows.reduce((sum, item) => sum + item.cases, 0);
  const highestBacklogRow = [...partitionRows].sort((left, right) => right.backlog - left.backlog)[0] ?? null;
  const latestRun = [...runs]
    .sort((left, right) => {
      const leftTime = new Date(left.updated_at || left.finished_at || left.created_at || 0).getTime();
      const rightTime = new Date(right.updated_at || right.finished_at || right.created_at || 0).getTime();
      return rightTime - leftTime;
    })[0] ?? null;
  const systemSignals = [
    {
      label: "Backlog pressure",
      value: String(highestBacklogRow?.backlog ?? 0),
      note: highestBacklogRow ? `${highestBacklogRow.name} queue highest` : "No backlog events",
    },
    {
      label: "Review queue",
      value: String(reviewCount),
      note: reviewCount > 0 ? "Runs need inspection" : "No review pending",
    },
    {
      label: "Last run",
      value: formatRelativeTime(latestRun?.updated_at || latestRun?.finished_at || latestRun?.created_at || null),
      note: latestRun ? `${latestRun.partition} ${latestRun.status}` : "No runtime runs yet",
    },
  ];

  return (
    <section className="overview-page">
      <header className="overview-page-header">
        <div className="overview-page-copy">
          <h2>Overview</h2>
          <p>Global status, partition distribution, and recent system changes.</p>
        </div>
      </header>

      <section className="overview-status-strip">
        <article className="overview-status-card">
          <div className="overview-status-head">
            <PanelMark>
              <IconPartition />
            </PanelMark>
            <span>Partitions</span>
          </div>
          <strong>{partitionRows.length}</strong>
          <small>{activePartitionCount} stable now</small>
        </article>
        <article className="overview-status-card">
          <div className="overview-status-head">
            <PanelMark>
              <IconTraceList />
            </PanelMark>
            <span>Cases</span>
          </div>
          <strong>{totalCases}</strong>
          <small>indexed</small>
        </article>
        <article className="overview-status-card">
          <div className="overview-status-head">
            <PanelMark>
              <IconBacklog />
            </PanelMark>
            <span>Backlog</span>
          </div>
          <strong>{backlogEvents.length}</strong>
          <small>{readyBacklogCount} ready</small>
        </article>
        <article className="overview-status-card">
          <div className="overview-status-head">
            <PanelMark>
              <IconRuns />
            </PanelMark>
            <span>Runs</span>
          </div>
          <strong>{runs.length}</strong>
          <small>{reviewCount} in review</small>
        </article>
      </section>

      <section className="overview-main-grid">
        <article className="skeleton-card overview-table-card">
          <div className="overview-panel-head">
            <div className="overview-panel-heading">
              <PanelMark>
                <IconOverview />
              </PanelMark>
              <h3>Partition List</h3>
            </div>
            <button type="button" className="overview-inline-button">Create</button>
          </div>
          <div className="overview-table-scroll">
            <div className="overview-table">
              <div className="overview-table-header">
                <span>Partition</span>
                <span>Cases</span>
                <span>Backlog</span>
                <span>Last run</span>
                <span>Status</span>
                <span>Active</span>
              </div>
              {loading ? <div className="overview-empty-state">Loading overview...</div> : null}
              {!loading && errorMessage ? <div className="overview-empty-state">{errorMessage}</div> : null}
              {!loading && !errorMessage && partitionRows.length === 0 ? (
                <div className="overview-empty-state">No partitions yet.</div>
              ) : null}
              {partitionRows.map((row) => (
                <div key={row.name} className="overview-table-row">
                  <strong>{row.name}</strong>
                  <span>{row.cases}</span>
                  <span>{row.backlog}</span>
                  <span>{formatRelativeTime(row.runAt)}</span>
                  <span className={`overview-inline-status is-${row.status}`}>{row.status}</span>
                  <button
                    type="button"
                    className={`overview-activate-button${activePartition === row.name ? " is-active" : ""}`}
                    onClick={() => onActivatePartition(row.name)}
                  >
                    {activePartition === row.name ? "On" : "Set"}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </article>

        <div className="overview-side-stack">
          <article className="skeleton-card overview-signal-card">
            <div className="overview-panel-head">
              <div className="overview-panel-heading">
                <PanelMark>
                  <IconRuns />
                </PanelMark>
                <h3>System Signals</h3>
              </div>
            </div>
            <div className="overview-signal-list">
              {systemSignals.map((item) => (
                <div key={item.label} className="overview-signal-row">
                  <div className="overview-signal-copy">
                    <strong>{item.label}</strong>
                    <span>{item.note}</span>
                  </div>
                  <em>{item.value}</em>
                </div>
              ))}
            </div>
          </article>

          <article className="skeleton-card overview-list-card">
            <div className="overview-panel-head">
              <div className="overview-panel-heading">
                <PanelMark>
                  <IconTraceList />
                </PanelMark>
                <h3>Recent Changes</h3>
              </div>
            </div>
            <div className="overview-list-scroll">
              <ul className="overview-compact-list">
                {loading ? <li>Loading recent changes...</li> : null}
                {!loading && errorMessage ? <li>{errorMessage}</li> : null}
                {!loading && !errorMessage && recentChanges.length === 0 ? <li>No recent changes.</li> : null}
                {recentChanges.map((item) => (
                  <li key={item.id}>
                    <strong>{item.label}</strong>
                    <span>{formatRelativeTime(item.timestamp)}</span>
                  </li>
                ))}
              </ul>
            </div>
          </article>
        </div>
      </section>
    </section>
  );
}
