import { requestJson } from "./base";

export type EventRecordResponse = {
  event_id: string;
  event_type: string;
  partition: string;
  resource_type: string;
  resource_id: string;
  status: string;
  priority: number;
  policy_id: string;
  ready_at: string | null;
  next_retry_at: string | null;
  last_run_at: string | null;
  run_id: string;
  batch_key: string;
  attempt_count: number;
  error_message: string;
  occurred_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  metadata: Record<string, unknown>;
};

export type BacklogMaintenanceActionResponse = {
  action: string;
  ok: boolean;
  summary: string;
  details: Record<string, unknown>;
};

export type PartitionTaskResponse = {
  task_id: string;
  partition: string;
  kind: string;
  payload: Record<string, unknown>;
  status: "queued" | "running" | "completed" | "failed" | "cancelled" | string;
  attempt_count: number;
  error_message: string;
  created_at: string | null;
  started_at: string | null;
  finished_at: string | null;
};

export function listBacklogEvents({
  partition,
  status = "",
  eventType = "",
}: {
  partition?: string;
  status?: string;
  eventType?: string;
}) {
  const search = new URLSearchParams();
  if (partition?.trim()) {
    search.set("partition", partition.trim());
  }
  if (status.trim()) {
    search.set("status", status.trim());
  }
  if (eventType.trim()) {
    search.set("event_type", eventType.trim());
  }
  const suffix = search.size > 0 ? `?${search.toString()}` : "";
  return requestJson<EventRecordResponse[]>(`/api/knowbase/runtime/backlog${suffix}`);
}

export function getBacklogEvent(eventId: string) {
  return requestJson<EventRecordResponse>(`/api/knowbase/runtime/backlog/${encodeURIComponent(eventId)}`);
}

export function listBacklogTasks({
  partition,
  status = "",
}: {
  partition?: string;
  status?: string;
}) {
  const search = new URLSearchParams();
  if (partition?.trim()) {
    search.set("partition", partition.trim());
  }
  if (status.trim()) {
    search.set("status", status.trim());
  }
  const suffix = search.size > 0 ? `?${search.toString()}` : "";
  return requestJson<PartitionTaskResponse[]>(`/api/knowbase/runtime/backlog/tasks${suffix}`);
}

export function getBacklogTask(taskId: string) {
  return requestJson<PartitionTaskResponse>(
    `/api/knowbase/runtime/backlog/tasks/${encodeURIComponent(taskId)}`,
  );
}

export function requeueBacklogEvent(eventId: string) {
  return requestJson<EventRecordResponse>(`/api/knowbase/runtime/backlog/${encodeURIComponent(eventId)}/requeue`, {
    method: "POST",
  });
}

export function deleteBacklogEvent(eventId: string) {
  return requestJson<{ deleted_type: string; deleted_id: string }>(
    `/api/knowbase/runtime/backlog/${encodeURIComponent(eventId)}`,
    { method: "DELETE" },
  );
}

export function drainBacklog(partition: string, limit = 20) {
  return requestJson<BacklogMaintenanceActionResponse>("/api/knowbase/runtime/maintenance/drain-backlog", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ partition, limit }),
  });
}
