import { requestJson } from "./base";

export type PartitionDocument = {
  partition_name: string;
  scenario_description: string;
  status: "active" | "disabled" | "archived";
  created_at: string;
  updated_at: string;
};

export type CreatePartitionRequest = {
  partition_name: string;
  scenario_description?: string;
  status?: "active" | "disabled" | "archived";
};

export type PartitionFacetDefinition = {
  key: string;
  display_name: string;
  description: string;
  examples: string[];
  enabled: boolean;
};

export type PartitionFacetSchemaResponse = {
  partition_name: string;
  facet_schema: {
    definitions: PartitionFacetDefinition[];
    metadata: Record<string, unknown>;
  };
  created_at: string | null;
  updated_at: string | null;
};

export type PartitionSemanticValueStat = {
  value: string;
  count: number;
};

export type PartitionSemanticKeyStat = {
  key: string;
  count: number;
  sample_values: PartitionSemanticValueStat[];
  aliases: string[];
  last_seen_at: string | null;
};

export type PartitionSemanticIndexDocument = {
  partition_name: string;
  semantic_index: {
    partition_name: string;
    key_stats: PartitionSemanticKeyStat[];
    metadata: Record<string, unknown>;
  };
  created_at: string;
  updated_at: string;
};

export type KnowbaseCaseDocument = {
  case_id: string;
  partition: string;
  created_at: string;
  updated_at: string;
  title: string;
  source_content: string;
  source_refs: string[];
  summary_text: string;
  facets?: Record<string, string[]>;
  semantic_profile?: Record<string, string[]>;
  metadata?: {
    author?: string;
    source?: string;
    status?: string;
  };
};

export type UpdateCaseRequest = {
  title?: string;
  source_content?: string;
};

export function getPartition(partitionName: string) {
  return requestJson<PartitionDocument>(`/api/knowbase/partitions/${encodeURIComponent(partitionName)}`);
}

export function listPartitions() {
  return requestJson<PartitionDocument[]>("/api/knowbase/partitions");
}

export function createPartition(payload: CreatePartitionRequest) {
  return requestJson<PartitionDocument>("/api/knowbase/partitions", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      partition_name: payload.partition_name,
      scenario_description: payload.scenario_description ?? "",
      status: payload.status ?? "active",
    }),
  });
}

export function updatePartition(partitionName: string, payload: CreatePartitionRequest) {
  return requestJson<PartitionDocument>(`/api/knowbase/partitions/${encodeURIComponent(partitionName)}`, {
    method: "PUT",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      partition_name: payload.partition_name,
      scenario_description: payload.scenario_description ?? "",
      status: payload.status ?? "active",
    }),
  });
}

export function deletePartition(partitionName: string) {
  return requestJson<{
    deleted_type: string;
    deleted_id: string;
    deleted_case_count: number;
    deleted_run_count: number;
    deleted_event_backlog_count: number;
  }>(`/api/knowbase/partitions/${encodeURIComponent(partitionName)}`, {
    method: "DELETE",
  });
}

export function getPartitionFacetSchema(partitionName: string) {
  return requestJson<PartitionFacetSchemaResponse>(
    `/api/knowbase/partitions/${encodeURIComponent(partitionName)}/facet-schema`,
  );
}

export function getPartitionSemanticIndex(partitionName: string) {
  return requestJson<PartitionSemanticIndexDocument>(
    `/api/knowbase/partitions/${encodeURIComponent(partitionName)}/semantic-index`,
  );
}

export type PartitionQueryStatistics = {
  partition: string;
  generated_at: string | null;
  query_count: number;
  query_key_stats: Record<string, number>;
  query_value_stats: Record<string, Record<string, number>>;
  metadata: Record<string, unknown>;
};

export function getPartitionQueryStatistics(partitionName: string) {
  return requestJson<PartitionQueryStatistics>(
    `/api/knowbase/partitions/${encodeURIComponent(partitionName)}/query-statistics`,
  );
}

export type PartitionCaseStatistics = {
  partition: string;
  generated_at: string | null;
  case_count: number;
  case_key_stats: Record<string, number>;
  case_value_stats: Record<string, Record<string, number>>;
};

export function getPartitionCaseStatistics(partitionName: string) {
  return requestJson<PartitionCaseStatistics>(
    `/api/knowbase/partitions/${encodeURIComponent(partitionName)}/case-statistics`,
  );
}

export function listPartitionCases(partitionName: string) {
  const search = new URLSearchParams({ partition: partitionName });
  return requestJson<KnowbaseCaseDocument[]>(`/api/knowbase/cases?${search.toString()}`);
}

export function getCase(caseId: string) {
  return requestJson<KnowbaseCaseDocument>(`/api/knowbase/cases/${encodeURIComponent(caseId)}`);
}

export function deleteCase(caseId: string) {
  return requestJson<{ deleted_type: string; deleted_id: string }>(
    `/api/knowbase/cases/${encodeURIComponent(caseId)}`,
    {
      method: "DELETE",
    },
  );
}

export function updateCase(caseId: string, payload: UpdateCaseRequest) {
  return requestJson<KnowbaseCaseDocument>(`/api/knowbase/cases/${encodeURIComponent(caseId)}`, {
    method: "PUT",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}
