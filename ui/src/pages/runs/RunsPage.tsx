import { useEffect, useMemo, useState } from "react";

import "./runs.css";
import { deleteRuntimeRun, getRuntimeRunTrace, listRuntimeRuns, type RuntimeRunSummary, type RuntimeTraceReplayResponse } from "../../shared/api";
import { RunsDetailPanel } from "./RunsDetailPanel";
import { RunsListPanel, type RunsStatusFilter } from "./RunsListPanel";
import type { MouseEvent } from "react";
import { useRef } from "react";

function formatTime(value: string | null) {
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

function formatStatus(status: string, requiresReview: boolean) {
  if (requiresReview) {
    return "review";
  }
  return status || "unknown";
}

export function RunsPage({ activePartition }: { activePartition: string | null }) {
  const [runs, setRuns] = useState<RuntimeRunSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [selectedTurnIndex, setSelectedTurnIndex] = useState<number>(0);
  const [trace, setTrace] = useState<RuntimeTraceReplayResponse | null>(null);
  const [statusFilter, setStatusFilter] = useState<RunsStatusFilter>("all");
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [loadingTrace, setLoadingTrace] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [deleteConfirmRunId, setDeleteConfirmRunId] = useState("");
  const [deletePopoverPosition, setDeletePopoverPosition] = useState<{ top: number; left: number } | null>(null);
  const [deleteErrorMessage, setDeleteErrorMessage] = useState("");
  const [actionPending, setActionPending] = useState("");
  const deletePopoverRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!activePartition?.trim()) {
      setRuns([]);
      setTrace(null);
      setSelectedRunId("");
      setErrorMessage("");
      setLoadingRuns(false);
      return () => {
        cancelled = true;
      };
    }
    setLoadingRuns(true);
    setErrorMessage("");
    setTrace(null);
    setSelectedRunId("");
    setSelectedTurnIndex(0);
    setStatusFilter("all");
    listRuntimeRuns(activePartition)
      .then((items) => {
        if (cancelled) {
          return;
        }
        setRuns(items);
        const requestedRunId = new URLSearchParams(window.location.search).get("run_id") ?? "";
        setSelectedRunId(items.some((item) => item.run_id === requestedRunId)
          ? requestedRunId
          : items[0]?.run_id ?? "");
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        setRuns([]);
        setErrorMessage(error instanceof Error ? error.message : "Failed to load runs.");
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingRuns(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [activePartition]);

  useEffect(() => {
    let cancelled = false;
    if (!selectedRunId) {
      setTrace(null);
      setSelectedTurnIndex(0);
      return () => {
        cancelled = true;
      };
    }
    setLoadingTrace(true);
    setSelectedTurnIndex(0);
    getRuntimeRunTrace(selectedRunId)
      .then((payload) => {
        if (!cancelled) {
          setTrace(payload);
          setSelectedTurnIndex(0);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setTrace(null);
          setSelectedTurnIndex(0);
          setErrorMessage(error instanceof Error ? error.message : "Failed to load trace.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingTrace(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedRunId]);

  useEffect(() => {
    if (!deleteConfirmRunId) {
      setDeletePopoverPosition(null);
      return;
    }

    function handlePointerDown(event: PointerEvent) {
      const target = event.target as HTMLElement | null;
      if (!target) {
        return;
      }
      if (deletePopoverRef.current?.contains(target)) {
        return;
      }
      if (target.closest(`[data-runs-delete-trigger="${deleteConfirmRunId}"]`)) {
        return;
      }
      setDeleteConfirmRunId("");
      setDeleteErrorMessage("");
    }

    function handleWindowChange() {
      setDeleteConfirmRunId("");
      setDeleteErrorMessage("");
    }

    window.addEventListener("pointerdown", handlePointerDown);
    window.addEventListener("resize", handleWindowChange);
    window.addEventListener("scroll", handleWindowChange, true);
    return () => {
      window.removeEventListener("pointerdown", handlePointerDown);
      window.removeEventListener("resize", handleWindowChange);
      window.removeEventListener("scroll", handleWindowChange, true);
    };
  }, [deleteConfirmRunId]);

  async function reloadRuns(nextSelectedRunId?: string) {
    if (!activePartition?.trim()) {
      return;
    }
    const items = await listRuntimeRuns(activePartition);
    setRuns(items);
    const nextFiltered = items.filter((item) => {
      if (statusFilter === "all") {
        return true;
      }
      if (statusFilter === "review") {
        return item.requires_review;
      }
      if (statusFilter === "completed") {
        return item.status === "completed" && !item.requires_review;
      }
      if (statusFilter === "failed") {
        return item.status === "failed";
      }
      return item.status === "running";
    });
    const fallbackId = nextSelectedRunId && nextFiltered.some((item) => item.run_id === nextSelectedRunId)
      ? nextSelectedRunId
      : nextFiltered[0]?.run_id ?? items[0]?.run_id ?? "";
    setSelectedRunId(fallbackId);
  }

  function toggleDeletePopover(runId: string, event: MouseEvent<HTMLButtonElement>) {
    event.stopPropagation();
    if (deleteConfirmRunId === runId) {
      setDeleteConfirmRunId("");
      setDeleteErrorMessage("");
      return;
    }
    if (selectedRunId !== runId) {
      setSelectedRunId(runId);
    }
    const rect = event.currentTarget.getBoundingClientRect();
    setDeletePopoverPosition({
      top: rect.top - 10,
      left: Math.max(12, rect.right - 280),
    });
    setDeleteConfirmRunId(runId);
    setDeleteErrorMessage("");
  }

  async function handleDeleteRun(runId: string) {
    if (!runId) {
      return;
    }
    setActionPending("delete");
    setDeleteErrorMessage("");
    try {
      await deleteRuntimeRun(runId);
      setDeleteConfirmRunId("");
      await reloadRuns(runId === selectedRunId ? "" : selectedRunId);
    } catch (error: unknown) {
      setDeleteErrorMessage(error instanceof Error ? error.message : "Failed to delete run.");
    } finally {
      setActionPending("");
    }
  }

  const counts = useMemo(
    () =>
      runs.reduce<Record<RunsStatusFilter, number>>(
        (acc, run) => {
          acc.all += 1;
          if (run.requires_review) {
            acc.review += 1;
          }
          if (run.status === "completed" && !run.requires_review) {
            acc.completed += 1;
          }
          if (run.status === "failed") {
            acc.failed += 1;
          }
          if (run.status === "running") {
            acc.running += 1;
          }
          return acc;
        },
        { all: 0, review: 0, completed: 0, failed: 0, running: 0 },
      ),
    [runs],
  );
  const filteredRuns = useMemo(() => {
    if (statusFilter === "all") {
      return runs;
    }
    if (statusFilter === "review") {
      return runs.filter((item) => item.requires_review);
    }
    if (statusFilter === "completed") {
      return runs.filter((item) => item.status === "completed" && !item.requires_review);
    }
    if (statusFilter === "failed") {
      return runs.filter((item) => item.status === "failed");
    }
    return runs.filter((item) => item.status === "running");
  }, [runs, statusFilter]);
  const selectedRun = useMemo(
    () => filteredRuns.find((item) => item.run_id === selectedRunId) ?? runs.find((item) => item.run_id === selectedRunId) ?? null,
    [filteredRuns, runs, selectedRunId],
  );

  useEffect(() => {
    if (filteredRuns.length === 0) {
      setSelectedRunId("");
      return;
    }
    if (!filteredRuns.some((item) => item.run_id === selectedRunId)) {
      setSelectedRunId(filteredRuns[0]?.run_id ?? "");
    }
  }, [filteredRuns, selectedRunId]);

  return (
    <section className="runs-page">
      <header className="runs-page-header">
        <div className="runs-page-copy">
          <h2>Runs</h2>
        </div>
      </header>

      <section className="runs-workbench">
        <RunsListPanel
          activePartition={activePartition}
          runs={filteredRuns}
          selectedRunId={selectedRunId}
          loadingRuns={loadingRuns}
          errorMessage={errorMessage}
          counts={counts}
          statusFilter={statusFilter}
          deleteErrorMessage={deleteErrorMessage}
          deleteConfirmRunId={deleteConfirmRunId}
          deletingRunId={actionPending === "delete" ? deleteConfirmRunId : ""}
          deletePopoverPosition={deletePopoverPosition}
          deletePopoverRef={deletePopoverRef}
          onSelectRun={setSelectedRunId}
          onChangeStatusFilter={setStatusFilter}
          onToggleDelete={toggleDeletePopover}
          onCancelDelete={() => {
            setDeleteConfirmRunId("");
            setDeleteErrorMessage("");
          }}
          onConfirmDelete={(runId) => void handleDeleteRun(runId)}
          formatTime={formatTime}
          formatStatus={formatStatus}
        />

        <RunsDetailPanel
          activePartition={activePartition}
          selectedRun={selectedRun}
          trace={trace}
          selectedTurnIndex={selectedTurnIndex}
          onSelectTurn={setSelectedTurnIndex}
          loadingTrace={loadingTrace}
          formatStatus={formatStatus}
        />
      </section>
    </section>
  );
}
