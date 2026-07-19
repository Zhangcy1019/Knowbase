import { requestJson } from "./base";

export type MaintenanceActionResponse = {
  action: string;
  ok: boolean;
  summary: string;
  details: Record<string, unknown>;
};

export type RuntimeRunSummary = {
  run_id: string;
  partition: string;
  agent_id: string;
  mode: string;
  status: string;
  requires_review: boolean;
  source_type: string;
  source_event_type: string;
  source_ref: string;
  objective: string;
  reasoning_summary: string;
  step_count: number;
  tool_call_count: number;
  skill_call_count: number;
  created_at: string | null;
  updated_at: string | null;
  finished_at: string | null;
};

export type RuntimeRunActionView = {
  action_name: string;
  action_type: string;
  target_type: string;
  target_id: string;
  summary: string;
};

export type RuntimeRunDetail = RuntimeRunSummary & {
  final_summary: string;
  planning_context: Record<string, unknown>;
  tool_whitelist: string[];
  skill_whitelist: string[];
  max_steps: number;
  max_tool_calls: number;
  max_skill_calls: number;
  risk_level: string;
  actions: RuntimeRunActionView[];
};

export type RuntimeRunStepResponse = {
  step_id: string;
  run_id: string;
  index: number;
  step_type: string;
  name: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  summary: string;
  created_at: string | null;
};

export type RuntimeRunArtifactResponse = {
  artifact_id: string;
  run_id: string;
  artifact_type: string;
  title: string;
  content: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
};

export type RuntimeTraceTurnResponse = {
  turn_index: number;
  decision_step: RuntimeRunStepResponse | null;
  decision_artifact: RuntimeRunArtifactResponse | null;
  planner_context_artifact: RuntimeRunArtifactResponse | null;
  llm_prompt_artifact: RuntimeRunArtifactResponse | null;
  llm_response_artifact: RuntimeRunArtifactResponse | null;
  action_steps: RuntimeRunStepResponse[];
  tool_calls: RuntimeRunStepResponse[];
  tool_results: RuntimeRunStepResponse[];
  skill_calls: RuntimeRunStepResponse[];
  skill_results: RuntimeRunStepResponse[];
  errors: RuntimeRunStepResponse[];
};

export type RuntimeTraceReplayResponse = {
  run: RuntimeRunDetail;
  request_artifact: RuntimeRunArtifactResponse | null;
  turns: RuntimeTraceTurnResponse[];
  steps: RuntimeRunStepResponse[];
  artifacts: RuntimeRunArtifactResponse[];
};

export function listRuntimeRuns(partition: string) {
  const search = new URLSearchParams();
  if (partition.trim()) {
    search.set("partition", partition.trim());
  }
  const suffix = search.size > 0 ? `?${search.toString()}` : "";
  return requestJson<RuntimeRunSummary[]>(`/api/knowbase/runtime/runs${suffix}`);
}

export function getRuntimeRunTrace(runId: string) {
  return requestJson<RuntimeTraceReplayResponse>(`/api/knowbase/runtime/runs/${encodeURIComponent(runId)}/trace`);
}

export function rebuildCase(caseId: string, partition: string) {
  return requestJson<MaintenanceActionResponse>(`/api/knowbase/runtime/maintenance/rebuild-case/${encodeURIComponent(caseId)}`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ partition }),
  });
}
