import { requestJson } from "./base";

export type KnowledgeDrainSummary = {
  decision_id: string;
  runtime_run_id: string;
  partition: string;
  batch_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  base_revision: string;
  applied_revision: string;
  mutation_plan_id: string;
  change_count: number;
  schema_changed: boolean;
  requires_review: boolean;
  error_message: string;
};

export type KnowledgeDrainDetail = KnowledgeDrainSummary & {
  input: {
    base_revision: string | null;
    statistics_fingerprint: string | null;
    statistics_snapshot: Record<string, unknown> | null;
    working_set: Record<string, unknown> | null;
  };
  stages: Record<string, {
    status: string;
    input?: Record<string, unknown> | null;
    output?: Record<string, unknown> | null;
    reasons?: string[];
    error?: string | null;
    captured_at?: string;
  }>;
  outcome: Record<string, unknown>;
  execution: Record<string, unknown> | null;
  status_history: Array<Record<string, unknown>>;
  reviewer: string | null;
  review_reason: string | null;
  supersedes_decision_id: string | null;
};

export type KnowledgeOverview = {
  partition: string;
  case_count: number;
  facet_key_count: number;
  pending_decision_count: number;
  last_drain_at: string | null;
};

export function listKnowledgeDrains(partition: string) {
  const search = new URLSearchParams();
  if (partition.trim()) {
    search.set("partition", partition.trim());
  }
  const suffix = search.size > 0 ? `?${search.toString()}` : "";
  return requestJson<KnowledgeDrainSummary[]>(`/api/knowbase/knowledge/drains${suffix}`);
}

export function getKnowledgeDrain(decisionId: string) {
  return requestJson<KnowledgeDrainDetail>(
    `/api/knowbase/knowledge/drains/${encodeURIComponent(decisionId)}`,
  );
}

export type KnowledgeReviewAction = "approve" | "discard" | "retry";

export function reviewKnowledgeDrain(
  decisionId: string,
  action: KnowledgeReviewAction,
  reason = "",
) {
  return requestJson<KnowledgeDrainDetail>(
    `/api/knowbase/knowledge/drains/${encodeURIComponent(decisionId)}/review`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, reviewer: "manual", reason }),
    },
  );
}

export function getKnowledgeOverview(partition: string) {
  const search = new URLSearchParams({ partition });
  return requestJson<KnowledgeOverview>(`/api/knowbase/knowledge/overview?${search.toString()}`);
}
