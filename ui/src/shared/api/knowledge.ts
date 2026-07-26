import { requestJson } from "./base";

export type KnowledgeDrainSummary = {
  decision_id: string;
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
  statistics_fingerprint: string;
  statistics_snapshot: Record<string, unknown>;
  working_set_snapshot: Record<string, unknown>;
  governance_result: Record<string, unknown>;
  mutation_plan: Record<string, unknown> | null;
  reviewer: string;
  review_reason: string;
  supersedes_decision_id: string;
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

export function getKnowledgeOverview(partition: string) {
  const search = new URLSearchParams({ partition });
  return requestJson<KnowledgeOverview>(`/api/knowbase/knowledge/overview?${search.toString()}`);
}
