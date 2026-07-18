import { requestJson } from "./base";

export type PartitionDocument = {
  partition_name: string;
  scenario_description: string;
  status: "active" | "disabled" | "archived";
  created_at: string;
  updated_at: string;
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

export function getPartition(partitionName: string) {
  return requestJson<PartitionDocument>(`/api/knowbase/partitions/${encodeURIComponent(partitionName)}`);
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

export function listPartitionCases(partitionName: string) {
  const search = new URLSearchParams({ partition: partitionName });
  return requestJson<KnowbaseCaseDocument[]>(`/api/knowbase/cases?${search.toString()}`);
}

export function getCase(caseId: string) {
  return requestJson<KnowbaseCaseDocument>(`/api/knowbase/cases/${encodeURIComponent(caseId)}`);
}
