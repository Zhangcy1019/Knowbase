import type { MouseEvent, ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

import "./backlog.css";
import { ConfirmDeletePopover } from "../../shared/component/confirm";
import {
  deleteBacklogEvent,
  drainBacklog,
  getBacklogEvent,
  listBacklogEvents,
  requeueBacklogEvent,
  type EventRecordResponse,
  type MaintenanceActionResponse,
} from "../../shared/api";
import { BacklogDetailPanel } from "./BacklogDetailPanel";
import { BacklogDrainConsole } from "./BacklogDrainConsole";
import { BacklogEventsList } from "./BacklogEventsList";

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

function formatDateTime(value: string | null) {
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
      if (event.status === "pending") {
        acc.pending += 1;
      }
      if (event.status === "failed") {
        acc.failed += 1;
      }
      if (event.status === "completed") {
        acc.completed += 1;
      }
      return acc;
    },
    { total: 0, pending: 0, failed: 0, completed: 0 },
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
  const [statusFilter, setStatusFilter] = useState<"all" | "pending" | "failed">("all");
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [actionPending, setActionPending] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [consoleMessage, setConsoleMessage] = useState("");
  const [deleteConfirmEventId, setDeleteConfirmEventId] = useState("");
  const [deletePopoverPosition, setDeletePopoverPosition] = useState<{ top: number; left: number } | null>(null);
  const [deleteErrorMessage, setDeleteErrorMessage] = useState("");
  const deletePopoverRef = useRef<HTMLDivElement | null>(null);
  const [drainConfirmOpen, setDrainConfirmOpen] = useState(false);
  const counts = useMemo(() => buildCounts(events), [events]);
  const eventTypeSummary = useMemo(() => summarizeEventTypes(events), [events]);
  const filteredEvents = useMemo(() => {
    if (statusFilter === "all") {
      return events;
    }
    if (statusFilter === "pending") {
      return events.filter((event) => event.status === "pending");
    }
    return events.filter((event) => event.status === "failed");
  }, [events, statusFilter]);

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

  useEffect(() => {
    if (!deleteConfirmEventId) {
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
      if (target.closest(`[data-backlog-delete-trigger="${deleteConfirmEventId}"]`)) {
        return;
      }
      setDeleteConfirmEventId("");
      setDeleteErrorMessage("");
    }

    function handleWindowChange() {
      setDeleteConfirmEventId("");
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
  }, [deleteConfirmEventId]);

  useEffect(() => {
    if (!drainConfirmOpen) {
      return;
    }

    function handlePointerDown(event: PointerEvent) {
      const target = event.target as HTMLElement | null;
      if (!target) {
        return;
      }
      if (target.closest(".backlog-drain-confirm")) {
        return;
      }
      if (target.closest("[data-backlog-drain-trigger='true']")) {
        return;
      }
      setDrainConfirmOpen(false);
    }

    function handleWindowChange() {
      setDrainConfirmOpen(false);
    }

    window.addEventListener("pointerdown", handlePointerDown);
    window.addEventListener("resize", handleWindowChange);
    window.addEventListener("scroll", handleWindowChange, true);
    return () => {
      window.removeEventListener("pointerdown", handlePointerDown);
      window.removeEventListener("resize", handleWindowChange);
      window.removeEventListener("scroll", handleWindowChange, true);
    };
  }, [drainConfirmOpen]);

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

  async function handleRequeue() {
    if (!selectedEvent) {
      return;
    }
    setActionPending("requeue");
    setErrorMessage("");
    try {
      const updated = await requeueBacklogEvent(selectedEvent.event_id);
      setConsoleMessage(`Requeued ${updated.event_id}.`);
      await reloadEvents(updated.event_id);
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to requeue event.");
    } finally {
      setActionPending("");
    }
  }

  async function handleDelete() {
    if (!selectedEvent) {
      return;
    }
    await handleDeleteEvent(selectedEvent.event_id);
  }

  async function handleDeleteEvent(eventId: string) {
    if (!eventId) {
      return;
    }
    setActionPending("delete");
    setDeleteErrorMessage("");
    try {
      await deleteBacklogEvent(eventId);
      setConsoleMessage(`Deleted ${eventId}.`);
      setDeleteConfirmEventId("");
      await reloadEvents();
    } catch (error: unknown) {
      setDeleteErrorMessage(error instanceof Error ? error.message : "Failed to delete event.");
    } finally {
      setActionPending("");
    }
  }

  function toggleDeletePopover(eventId: string, event: MouseEvent<HTMLButtonElement>) {
    event.stopPropagation();
    if (deleteConfirmEventId === eventId) {
      setDeleteConfirmEventId("");
      setDeleteErrorMessage("");
      return;
    }
    if (selectedEventId !== eventId) {
      setSelectedEventId(eventId);
    }
    const rect = event.currentTarget.getBoundingClientRect();
    setDeletePopoverPosition({
      top: rect.top - 10,
      left: Math.max(12, rect.right - 280),
    });
    setDeleteConfirmEventId(eventId);
    setDeleteErrorMessage("");
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
      setDrainConfirmOpen(false);
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

      <BacklogDrainConsole
        activePartition={activePartition}
        counts={counts}
        eventTypeSummary={eventTypeSummary}
        actionPending={actionPending}
        consoleMessage={consoleMessage}
        onDrain={() => setDrainConfirmOpen(true)}
      />
      {drainConfirmOpen ? (
        <div className="backlog-drain-confirm-shell">
          <ConfirmDeletePopover
            className="backlog-drain-confirm"
            title="Drain backlog now?"
            description="This will process all currently pending backlog events in the active partition."
            confirmLabel="Drain"
            pendingLabel="Draining..."
            pending={actionPending === "drain"}
            onCancel={() => setDrainConfirmOpen(false)}
            onConfirm={() => void handleDrain()}
          />
        </div>
      ) : null}

      <section className="backlog-workbench">
        <BacklogEventsList
          activePartition={activePartition}
          counts={counts}
          statusFilter={statusFilter}
          filteredEvents={filteredEvents}
          selectedEventId={selectedEventId}
          loadingEvents={loadingEvents}
          errorMessage={errorMessage}
          deleteErrorMessage={deleteErrorMessage}
          deleteConfirmEventId={deleteConfirmEventId}
          deletingEventId={actionPending === "delete" ? selectedEvent?.event_id || "" : ""}
          deletePopoverPosition={deletePopoverPosition}
          deletePopoverRef={deletePopoverRef}
          onSelectEvent={setSelectedEventId}
          onChangeStatusFilter={setStatusFilter}
          onToggleDelete={toggleDeletePopover}
          onCancelDelete={() => {
            setDeleteConfirmEventId("");
            setDeleteErrorMessage("");
          }}
          onConfirmDelete={(eventId) => void handleDeleteEvent(eventId)}
          formatTime={formatTime}
        />

        <BacklogDetailPanel
          activePartition={activePartition}
          selectedEvent={selectedEvent}
          selectedResourceRef={selectedResourceRef}
          lastRunAt={lastRunAt}
          loadingDetail={loadingDetail}
          actionPending={actionPending}
          onRequeue={() => void handleRequeue()}
          formatDateTime={formatDateTime}
        />
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
