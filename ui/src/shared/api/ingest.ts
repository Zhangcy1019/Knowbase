import { requestJson } from "./base";

export type IngestRequest = {
  partition: string;
  title: string;
  source_content: string;
  source_refs: string[];
};

export type IngestResponse = {
  created_type: string;
  created_id: string;
  partition: string;
  detail: {
    accepted?: boolean;
    processing_status?: string;
    backlog_event_id?: string;
  };
};

export function createKnowbaseCase(request: IngestRequest) {
  return requestJson<IngestResponse>("/api/knowbase/cases", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      partition: request.partition,
      title: request.title,
      source_content: request.source_content,
      source_refs: request.source_refs,
    }),
  });
}
