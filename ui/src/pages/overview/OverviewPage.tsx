import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import "./overview.css";
import { ConfirmDeletePopover } from "../../shared/component/confirm";
import { IconBacklog, IconOverview, IconPartition, IconRuns, IconTraceList } from "../../shared/icons";
import {
  deletePartition,
  listBacklogEvents,
  listPartitionCases,
  listPartitions,
  listRuntimeRuns,
  updatePartition,
  type EventRecordResponse,
  type PartitionDocument,
  type RuntimeRunSummary,
} from "../../shared/api";
import { PartitionCreateModal } from "./PartitionCreateModal";

type OverviewPartitionRow = {
  name: string;
  cases: number;
  backlog: number;
  runAt: string | null;
  statusTone: "stable" | "elevated" | "review";
};

type OverviewRecentChange = {
  id: string;
  label: string;
  timestamp: string | null;
};

type ManagerMode = "view" | "edit";

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

function formatAbsoluteTime(value: string | null) {
  if (!value) {
    return "--";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString([], {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function resolvePartitionTone(
  partition: PartitionDocument,
  backlogCount: number,
  runs: RuntimeRunSummary[],
): OverviewPartitionRow["statusTone"] {
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
  const [partitions, setPartitions] = useState<PartitionDocument[]>([]);
  const [partitionRows, setPartitionRows] = useState<OverviewPartitionRow[]>([]);
  const [backlogEvents, setBacklogEvents] = useState<EventRecordResponse[]>([]);
  const [runs, setRuns] = useState<RuntimeRunSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [selectedPartitionName, setSelectedPartitionName] = useState("");
  const [managerMode, setManagerMode] = useState<ManagerMode>("view");
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [managerError, setManagerError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [formDescription, setFormDescription] = useState("");
  const [formStatus, setFormStatus] = useState<PartitionDocument["status"]>("active");

  async function loadOverview(isCancelled?: () => boolean) {
    setLoading(true);
    setErrorMessage("");
    try {
      const [nextPartitions, events, runtimeRuns] = await Promise.all([
        listPartitions(),
        listBacklogEvents({}),
        listRuntimeRuns(""),
      ]);
      const nextRows = await Promise.all(
        nextPartitions.map(async (partition) => {
          const [cases, partitionRuns, partitionEvents] = await Promise.all([
            listPartitionCases(partition.partition_name),
            Promise.resolve(runtimeRuns.filter((item) => item.partition === partition.partition_name)),
            Promise.resolve(events.filter((item) => item.partition === partition.partition_name)),
          ]);
          const lastRunAt =
            partitionRuns
              .map((item) => item.updated_at || item.finished_at || item.created_at)
              .filter((item): item is string => Boolean(item))
              .sort((left, right) => new Date(right).getTime() - new Date(left).getTime())[0] ?? null;
          return {
            name: partition.partition_name,
            cases: cases.length,
            backlog: partitionEvents.length,
            runAt: lastRunAt,
            statusTone: resolvePartitionTone(partition, partitionEvents.length, partitionRuns),
          } satisfies OverviewPartitionRow;
        }),
      );
      nextRows.sort((left, right) => left.name.localeCompare(right.name));
      if (isCancelled?.()) {
        return;
      }
      setPartitions(nextPartitions);
      setPartitionRows(nextRows);
      setBacklogEvents(events);
      setRuns(runtimeRuns);
      setSelectedPartitionName((current) => {
        if (current && nextPartitions.some((item) => item.partition_name === current)) {
          return current;
        }
        return nextPartitions[0]?.partition_name ?? "";
      });
    } catch (error: unknown) {
      if (isCancelled?.()) {
        return;
      }
      setPartitions([]);
      setPartitionRows([]);
      setBacklogEvents([]);
      setRuns([]);
      setErrorMessage(error instanceof Error ? error.message : "Failed to load overview.");
    } finally {
      if (!isCancelled?.()) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    let cancelled = false;
    void loadOverview(() => cancelled);
    return () => {
      cancelled = true;
    };
  }, []);

  const recentChanges = useMemo(() => buildRecentChanges(backlogEvents, runs), [backlogEvents, runs]);
  const reviewCount = runs.filter((item) => item.requires_review).length;
  const readyBacklogCount = backlogEvents.filter((item) => item.status === "ready").length;
  const activePartitionCount = partitions.filter((item) => item.status === "active").length;
  const totalCases = partitionRows.reduce((sum, item) => sum + item.cases, 0);
  const selectedPartition = partitions.find((item) => item.partition_name === selectedPartitionName) ?? null;
  const selectedRow = partitionRows.find((item) => item.name === selectedPartitionName) ?? null;
  const busiestPartition = [...partitionRows].sort((left, right) => right.backlog - left.backlog)[0] ?? null;
  const latestRun = [...runs]
    .sort((left, right) => {
      const leftTime = new Date(left.updated_at || left.finished_at || left.created_at || 0).getTime();
      const rightTime = new Date(right.updated_at || right.finished_at || right.created_at || 0).getTime();
      return rightTime - leftTime;
    })[0] ?? null;
  const bottomSignals = [
    {
      label: "Backlog pressure",
      value: String(busiestPartition?.backlog ?? 0),
      note: busiestPartition ? `${busiestPartition.name} queue highest` : "No backlog events",
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

  function enterCreateMode() {
    setCreateModalOpen(true);
    setManagerError("");
    setDeleteConfirmOpen(false);
  }

  function enterEditMode() {
    if (!selectedPartition) {
      return;
    }
    setManagerMode("edit");
    setManagerError("");
    setDeleteConfirmOpen(false);
    setFormDescription(selectedPartition.scenario_description || "");
    setFormStatus(selectedPartition.status);
  }

  function resetManagerMode() {
    setManagerMode("view");
    setManagerError("");
    setDeleteConfirmOpen(false);
  }

  async function handleSubmitManager() {
    if (managerMode !== "edit" || !selectedPartition) {
      return;
    }
    try {
      setSubmitting(true);
      setManagerError("");
      const updated = await updatePartition(selectedPartition.partition_name, {
        partition_name: selectedPartition.partition_name,
        scenario_description: formDescription.trim(),
        status: formStatus,
      });
      await loadOverview();
      setSelectedPartitionName(updated.partition_name);
      if (activePartition === updated.partition_name && updated.status !== "active") {
        onActivatePartition(null);
      }
      setManagerMode("view");
    } catch (error: unknown) {
      setManagerError(error instanceof Error ? error.message : "Partition update failed.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCreatedPartition(created: PartitionDocument) {
    await loadOverview();
    setSelectedPartitionName(created.partition_name);
    onActivatePartition(created.partition_name);
  }

  async function handleDeleteSelected() {
    if (!selectedPartition) {
      return;
    }
    try {
      setSubmitting(true);
      setManagerError("");
      setDeleteConfirmOpen(false);
      const nextSelectedPartitionName =
        partitions.find((item) => item.partition_name !== selectedPartition.partition_name)?.partition_name ?? "";
      await deletePartition(selectedPartition.partition_name);
      if (activePartition === selectedPartition.partition_name) {
        onActivatePartition(null);
      }
      setSelectedPartitionName(nextSelectedPartitionName);
      await loadOverview();
      setManagerMode("view");
    } catch (error: unknown) {
      setManagerError(error instanceof Error ? error.message : "Partition delete failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="overview-page">
      <header className="overview-page-header">
        <div className="overview-page-copy">
          <h2>Overview</h2>
          <p>Global status and partition management.</p>
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
          <strong>{partitions.length}</strong>
          <small>{activePartitionCount} active</small>
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

      <section className="overview-manager-grid">
        <article className="skeleton-card overview-manager-list-card">
          <div className="overview-panel-head">
            <div className="overview-panel-heading">
              <PanelMark>
                <IconOverview />
              </PanelMark>
              <h3>Partition Manager</h3>
            </div>
            <button type="button" className="overview-inline-button" onClick={enterCreateMode}>
              Create
            </button>
          </div>

          <div className="overview-table-scroll">
            <div className="overview-table">
              <div className="overview-table-header">
                <span>Partition</span>
                <span>Summary</span>
                <span>Cases</span>
                <span>Backlog</span>
                <span>Status</span>
                <span>Active</span>
              </div>
              {loading && partitionRows.length === 0 ? <div className="overview-empty-state">Loading partitions...</div> : null}
              {!loading && errorMessage ? <div className="overview-empty-state">{errorMessage}</div> : null}
              {!loading && !errorMessage && partitionRows.length === 0 ? (
                <div className="overview-empty-state">No partitions yet.</div>
              ) : null}
              {partitionRows.map((row) => {
                const partition = partitions.find((item) => item.partition_name === row.name);
                return (
                  <button
                    key={row.name}
                    type="button"
                    className={`overview-table-row overview-table-row-button${selectedPartitionName === row.name ? " is-selected" : ""}`}
                    onClick={() => {
                      setSelectedPartitionName(row.name);
                      setManagerMode("view");
                      setManagerError("");
                      setDeleteConfirmOpen(false);
                    }}
                  >
                    <strong>{row.name}</strong>
                    <span className="overview-table-summary">
                      {partition?.scenario_description || "No description"}
                    </span>
                    <span>{row.cases}</span>
                    <span>{row.backlog}</span>
                    <span className={`overview-inline-status is-${row.statusTone}`}>{partition?.status || "active"}</span>
                    <button
                      type="button"
                      className={`overview-activate-button${activePartition === row.name ? " is-active" : ""}`}
                      onClick={(event) => {
                        event.stopPropagation();
                        onActivatePartition(row.name);
                      }}
                    >
                      {activePartition === row.name ? "On" : "Set"}
                    </button>
                  </button>
                );
              })}
            </div>
          </div>
        </article>

        <article className="skeleton-card overview-manager-detail-card">
          <div className="overview-panel-head">
            <div className="overview-panel-heading">
              <PanelMark>
                <IconPartition />
              </PanelMark>
              <h3>
                {managerMode === "edit" ? "Edit Partition" : "Partition Detail"}
              </h3>
            </div>
            {managerMode === "view" && selectedPartition ? (
              <div className="overview-action-strip overview-delete-anchor">
                <button type="button" className="overview-inline-button" onClick={enterEditMode}>
                  Edit
                </button>
                <button
                  type="button"
                  className="overview-inline-button is-danger"
                  onClick={() => {
                    setDeleteConfirmOpen((current) => !current);
                    setManagerError("");
                  }}
                >
                  Delete
                </button>
                {deleteConfirmOpen ? (
                  <ConfirmDeletePopover
                    className="overview-delete-popover"
                    title={`Delete ${selectedPartition.partition_name}?`}
                    description="This will remove the partition and cascade its cases and runs."
                    errorMessage={managerError}
                    pending={submitting}
                    onCancel={() => {
                      setDeleteConfirmOpen(false);
                      setManagerError("");
                    }}
                    onConfirm={handleDeleteSelected}
                  />
                ) : null}
              </div>
            ) : null}
          </div>

          {managerMode === "edit" ? (
            <div className="overview-manager-form">
              <label className="overview-create-field">
                <span>Name</span>
                <input
                  disabled
                  value={selectedPartition?.partition_name || ""}
                  placeholder="Claims"
                />
              </label>
              <label className="overview-create-field">
                <span>Description</span>
                <textarea
                  rows={4}
                  disabled={submitting}
                  value={formDescription}
                  onChange={(event) => setFormDescription(event.target.value)}
                  placeholder="Scope, domain, and curation intent."
                />
              </label>
              <label className="overview-create-field">
                <span>Status</span>
                <select
                  disabled={submitting}
                  value={formStatus}
                  onChange={(event) => setFormStatus(event.target.value as PartitionDocument["status"])}
                >
                  <option value="active">active</option>
                  <option value="disabled">disabled</option>
                  <option value="archived">archived</option>
                </select>
              </label>
              {managerError ? <div className="overview-manager-error">{managerError}</div> : null}
              <div className="overview-manager-actions overview-manager-actions-bottom">
                <button type="button" className="overview-inline-button" onClick={resetManagerMode} disabled={submitting}>
                  Cancel
                </button>
                <button type="button" className="overview-primary-button" onClick={handleSubmitManager} disabled={submitting}>
                  {submitting ? "Saving..." : "Submit"}
                </button>
              </div>
            </div>
          ) : null}

          {managerMode === "view" ? (
            selectedPartition && selectedRow ? (
              <div className="overview-detail-stack">
                <article className="overview-detail-hero">
                  <strong>{selectedPartition.partition_name}</strong>
                  <p>{selectedPartition.scenario_description || "No description."}</p>
                </article>

                <div className="overview-detail-stats">
                  <div className="overview-detail-stat">
                    <span>Status</span>
                    <strong>{selectedPartition.status}</strong>
                  </div>
                  <div className="overview-detail-stat">
                    <span>Cases</span>
                    <strong>{selectedRow.cases}</strong>
                  </div>
                  <div className="overview-detail-stat">
                    <span>Backlog</span>
                    <strong>{selectedRow.backlog}</strong>
                  </div>
                  <div className="overview-detail-stat">
                    <span>Last run</span>
                    <strong>{formatRelativeTime(selectedRow.runAt)}</strong>
                  </div>
                </div>

                <article className="overview-detail-meta">
                  <span>Created</span>
                  <strong>{formatAbsoluteTime(selectedPartition.created_at)}</strong>
                  <span>Updated</span>
                  <strong>{formatAbsoluteTime(selectedPartition.updated_at)}</strong>
                </article>
              </div>
            ) : (
              <div className="overview-empty-state">Select a partition to inspect.</div>
            )
          ) : null}
        </article>
      </section>

      <section className="overview-bottom-grid">
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

        <article className="skeleton-card overview-list-card">
          <div className="overview-panel-head">
            <div className="overview-panel-heading">
              <PanelMark>
                <IconRuns />
              </PanelMark>
              <h3>System Signals</h3>
            </div>
          </div>
          <div className="overview-signal-list">
            {bottomSignals.map((item) => (
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
      </section>

      <PartitionCreateModal
        open={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onCreated={handleCreatedPartition}
      />
    </section>
  );
}
