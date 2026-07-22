import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import { IconTraceDetail, IconTraceFocus, IconTraceLoop } from "../../shared/icons";
import type {
  RuntimeRunArtifactResponse,
  RuntimeRunSummary,
  RuntimeRunStepResponse,
  RuntimeTraceReplayResponse,
  RuntimeTraceTurnResponse,
} from "../../shared/api";

type RunsDetailPanelProps = {
  activePartition: string | null;
  selectedRun: RuntimeRunSummary | null;
  trace: RuntimeTraceReplayResponse | null;
  selectedTurnIndex: number;
  onSelectTurn: (turnIndex: number) => void;
  loadingTrace: boolean;
  formatStatus: (status: string, requiresReview: boolean) => string;
};

type FlowItem = {
  key: string;
  kind: "run" | "execution" | "verification" | "outcome";
  title: string;
  detail: string;
  meta: string;
  tone: "neutral" | "success" | "warning" | "danger";
};

function PanelMark({ children }: { children: ReactNode }) {
  return <span className="runs-panel-mark">{children}</span>;
}

function formatCompactTime(value: string | null) {
  if (!value) {
    return "--";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString([], {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function buildPromptLines(turn: RuntimeTraceTurnResponse | null) {
  const artifactContent = turn?.llm_prompt_artifact?.content;
  if (!artifactContent || typeof artifactContent !== "object") {
    return ["No prompt artifact available."];
  }
  const sections: string[] = [];
  const system = typeof artifactContent.system === "string" ? artifactContent.system.trim() : "";
  const instruction = typeof artifactContent.instruction === "string" ? artifactContent.instruction.trim() : "";
  if (system) {
    sections.push("[System]", system);
  }
  if (instruction) {
    sections.push("[Instruction]", instruction);
  }
  if (sections.length === 0) {
    return ["No prompt artifact available."];
  }
  return sections.join("\n\n").split("\n").filter((line) => line.length > 0);
}

function buildResponseLines(turn: RuntimeTraceTurnResponse | null) {
  const artifactContent = turn?.llm_response_artifact?.content;
  if (!artifactContent) {
    return ["No response artifact available."];
  }
  const payload = typeof artifactContent === "object" && artifactContent !== null && "payload" in artifactContent
    ? artifactContent.payload
    : artifactContent;
  return JSON.stringify(payload, null, 2).split("\n");
}

function buildTurnArtifacts(turn: RuntimeTraceTurnResponse | null) {
  if (!turn) {
    return [];
  }
  return [
    turn.decision_artifact,
    turn.planner_context_artifact,
    turn.llm_prompt_artifact,
    turn.llm_response_artifact,
  ].filter((artifact): artifact is RuntimeRunArtifactResponse => artifact !== null);
}

function buildTurnMeta(turn: RuntimeTraceTurnResponse) {
  const parts = [
    `${turn.action_steps.length} action`,
    `${turn.tool_calls.length} tool`,
    `${turn.skill_calls.length} skill`,
  ];
  if (turn.errors.length > 0) {
    parts.push(`${turn.errors.length} error`);
  }
  const createdAt = turn.decision_step?.created_at ?? turn.action_steps[0]?.created_at ?? null;
  parts.push(formatCompactTime(createdAt));
  return parts;
}

function buildTurnOverview(turn: RuntimeTraceTurnResponse | null) {
  if (!turn) {
    return {
      shouldStop: "--",
      actionCount: 0,
      finishReason: "--",
      createdAt: "--",
      errorCount: 0,
    };
  }
  const responseContent = turn.llm_response_artifact?.content;
  const responsePayload = typeof responseContent === "object" && responseContent !== null && "payload" in responseContent
    ? responseContent.payload
    : null;
  const finishReason = typeof responseContent === "object" && responseContent !== null && "finish_reason" in responseContent
    ? String(responseContent.finish_reason || "--")
    : "--";
  const shouldStop = typeof responsePayload === "object" && responsePayload !== null && "should_stop" in responsePayload
    ? (responsePayload.should_stop ? "yes" : "no")
    : "--";
  const actionCount = Array.isArray((responsePayload as { actions?: unknown[] } | null)?.actions)
    ? (responsePayload as { actions: unknown[] }).actions.length
    : turn.action_steps.length;
  const createdAt =
    turn.decision_step?.created_at ?? turn.llm_response_artifact?.created_at ?? turn.llm_prompt_artifact?.created_at ?? null;
  return {
    shouldStop,
    actionCount,
    finishReason,
    createdAt: formatCompactTime(createdAt),
    errorCount: turn.errors.length,
  };
}

function getObservationRows(step: RuntimeRunStepResponse) {
  const output = step.output && typeof step.output === "object" ? step.output : {};
  return {
    kind: typeof output.kind === "string" ? output.kind : "",
    status: typeof output.status === "string" ? output.status : "",
    summary: typeof output.summary === "string" ? output.summary : "",
  };
}

function buildFlowItems(trace: RuntimeTraceReplayResponse | null): FlowItem[] {
  if (!trace) {
    return [];
  }
  const items: FlowItem[] = [];
  const observationSteps = trace.steps.filter((step) => step.step_type === "observation");
  const totalTurnCount = trace.turns.length;
  const totalSkillCalls = trace.turns.reduce((sum, turn) => sum + turn.skill_calls.length, 0);
  const totalToolCalls = trace.turns.reduce((sum, turn) => sum + turn.tool_calls.length, 0);
  const totalErrors = trace.turns.reduce((sum, turn) => sum + turn.errors.length, 0);
  const latestTurnSummary =
    [...trace.turns]
      .reverse()
      .map((turn) => turn.decision_step?.summary?.trim() || "")
      .find(Boolean) || "Loop executed.";

  items.push({
    key: "run-start",
    kind: "run",
    title: "Run",
    detail: trace.run.objective || trace.run.run_id,
    meta: trace.run.status,
    tone: trace.run.status === "failed" ? "danger" : trace.run.requires_review ? "warning" : "neutral",
  });

  if (totalTurnCount > 0) {
    items.push({
      key: "execution",
      kind: "execution",
      title: "Execution",
      detail: latestTurnSummary,
      meta: `${totalTurnCount} turn · ${totalSkillCalls} skill · ${totalToolCalls} tool`,
      tone: totalErrors > 0 ? "danger" : "neutral",
    });
  }

  if (observationSteps.length > 0) {
    const verificationRows = observationSteps.map((step, index) => {
      const row = getObservationRows(step);
      return {
        key: `observation-${step.step_id}`,
        kind: row.kind || step.name || `observation-${index}`,
        status: row.status || "recorded",
        summary: row.summary || step.summary || "Observation recorded.",
      };
    });
    const latestVerification = verificationRows[verificationRows.length - 1];
    const verificationCount = verificationRows.filter((row) => row.kind === "verification_subrun").length;
    const feedbackCount = verificationRows.filter((row) => row.kind === "verification_feedback").length;
    const verificationTone =
      latestVerification.status === "failed"
        ? "danger"
        : latestVerification.status === "completed"
          ? "success"
          : latestVerification.status === "requires_review"
            ? "warning"
            : "neutral";

    items.push({
      key: "verification",
      kind: "verification",
      title: "Verification",
      detail: latestVerification.summary,
      meta: `${verificationCount} subrun · ${feedbackCount} feedback · ${latestVerification.status}`,
      tone: verificationTone,
    });
  }

  if (trace.run.final_summary) {
    items.push({
      key: "run-final",
      kind: "outcome",
      title: "Outcome",
      detail: trace.run.final_summary,
      meta: trace.run.status,
      tone: trace.run.status === "failed" ? "danger" : trace.run.requires_review ? "warning" : "success",
    });
  } else if (totalErrors > 0) {
    const latestError =
      [...trace.turns]
        .reverse()
        .flatMap((turn) => turn.errors)
        .map((step) => step.summary.trim())
        .find(Boolean) || "Execution ended with errors.";
    items.push({
      key: "run-final-fallback",
      kind: "outcome",
      title: "Outcome",
      detail: latestError,
      meta: trace.run.status,
      tone: "danger",
    });
  }

  return items;
}

function buildOverview(
  trace: RuntimeTraceReplayResponse | null,
  selectedRun: RuntimeRunSummary | null,
  formatStatus: RunsDetailPanelProps["formatStatus"],
) {
  const run = trace?.run ?? selectedRun;
  const observationSteps = trace?.steps.filter((step) => step.step_type === "observation") ?? [];
  const verificationStep = observationSteps.find((step) => getObservationRows(step).kind === "verification_subrun");
  const verificationStatus = verificationStep ? getObservationRows(verificationStep).status || "recorded" : "not triggered";
  return {
    objective: run?.objective || "Select a run to inspect runtime flow.",
    finalSummary: trace?.run.final_summary || run?.reasoning_summary || "No final summary available.",
    status: run ? formatStatus(run.status, run.requires_review) : "--",
    partition: run?.partition || "--",
    startedAt: formatCompactTime(run?.created_at ?? null),
    finishedAt: formatCompactTime(run?.finished_at ?? null),
    turnCount: trace?.turns.length ?? 0,
    verificationStatus,
  };
}

export function RunsDetailPanel({
  activePartition,
  selectedRun,
  trace,
  selectedTurnIndex,
  onSelectTurn,
  loadingTrace,
  formatStatus,
}: RunsDetailPanelProps) {
  const turns = trace?.turns ?? [];
  const selectedTurn = turns[selectedTurnIndex] ?? turns[0] ?? null;
  const [expandedArtifactId, setExpandedArtifactId] = useState("");
  const [promptOpen, setPromptOpen] = useState(false);
  const [responseOpen, setResponseOpen] = useState(false);
  const promptLines = buildPromptLines(selectedTurn);
  const responseLines = buildResponseLines(selectedTurn);
  const artifactRows = buildTurnArtifacts(selectedTurn);
  const turnOverview = buildTurnOverview(selectedTurn);
  const flowItems = useMemo(() => buildFlowItems(trace), [trace]);
  const overview = useMemo(() => buildOverview(trace, selectedRun, formatStatus), [trace, selectedRun, formatStatus]);

  useEffect(() => {
    setExpandedArtifactId("");
    setPromptOpen(false);
    setResponseOpen(false);
  }, [selectedTurnIndex, selectedRun?.run_id]);

  return (
    <div className="runs-detail-stack">
      <article className="skeleton-card runs-summary-card">
        <div className="runs-panel-head">
          <div className="runs-panel-heading">
            <PanelMark>
              <IconTraceFocus />
            </PanelMark>
            <h3>Overview</h3>
          </div>
          <code>{selectedRun?.partition || activePartition || "No active partition"}</code>
        </div>

        <div className="runs-summary-grid is-orchestrated">
          <div className="runs-summary-hero">
            <strong>{overview.objective}</strong>
          </div>

          <div className="runs-summary-stats">
            <div className="runs-stat-card">
              <span>Status</span>
              <strong>{overview.status}</strong>
            </div>
            <div className="runs-stat-card">
              <span>Turns</span>
              <strong>{overview.turnCount}</strong>
            </div>
            <div className="runs-stat-card">
              <span>Verification</span>
              <strong>{overview.verificationStatus}</strong>
            </div>
            <div className="runs-stat-card">
              <span>Started</span>
              <strong>{overview.startedAt}</strong>
            </div>
            <div className="runs-stat-card">
              <span>Finished</span>
              <strong>{overview.finishedAt}</strong>
            </div>
          </div>
        </div>
      </article>

      <article className="skeleton-card runs-flow-card">
        <div className="runs-panel-head">
          <div className="runs-panel-heading">
            <PanelMark>
              <IconTraceLoop />
            </PanelMark>
            <h3>Flow</h3>
          </div>
        </div>
        <div className="runs-flow-list">
          {loadingTrace ? <div className="runs-empty-state">Loading trace...</div> : null}
          {!loadingTrace && !trace ? <div className="runs-empty-state">No flow loaded.</div> : null}
          {!loadingTrace &&
            flowItems.map((item) => (
              <div key={item.key} className={`runs-flow-row is-${item.tone}`}>
                <div className="runs-flow-marker" />
                <div className="runs-flow-copy">
                  <div className="runs-flow-head">
                    <strong>{item.title}</strong>
                    <span>{item.meta}</span>
                  </div>
                  <p>{item.detail}</p>
                </div>
              </div>
            ))}
        </div>
      </article>

      <section className="runs-trace-grid">
        <article className="skeleton-card runs-turn-card">
          <div className="runs-panel-head">
            <div className="runs-panel-heading">
              <PanelMark>
                <IconTraceLoop />
              </PanelMark>
              <h3>Trace</h3>
            </div>
          </div>

          <div className="runs-turn-scroll">
            <div className="runs-turn-list">
              {loadingTrace ? <div className="runs-empty-state">Loading trace...</div> : null}
              {!loadingTrace && !trace ? <div className="runs-empty-state">No trace loaded.</div> : null}
              {turns.map((turn, index) => (
                <button
                  key={`${turn.turn_index}`}
                  type="button"
                  className={`runs-turn-row${index === selectedTurnIndex ? " is-active" : ""}`}
                  onClick={() => onSelectTurn(index)}
                >
                  <div className="runs-turn-marker" />
                  <div className="runs-turn-body">
                    <div className="runs-turn-head">
                      <strong>{String(turn.turn_index).padStart(2, "0")}</strong>
                      <span>{turn.decision_step?.summary || turn.decision_step?.step_type || "turn"}</span>
                    </div>
                    <div className="runs-turn-meta">
                      {buildTurnMeta(turn).map((item) => (
                        <span key={`${turn.turn_index}-${item}`}>{item}</span>
                      ))}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </article>

        <article className="skeleton-card runs-detail-card">
          <div className="runs-panel-head">
            <div className="runs-panel-heading">
              <PanelMark>
                <IconTraceDetail />
              </PanelMark>
              <h3>Turn {selectedTurn ? String(selectedTurn.turn_index).padStart(2, "0") : "--"}</h3>
            </div>
          </div>

          <div className="runs-detail-scroll">
            <section className="runs-detail-section">
              <div className="runs-detail-title">
                <strong>Decision</strong>
                <span>turn_state</span>
              </div>
              <div className="runs-turn-overview-grid">
                <div className="runs-turn-overview-card">
                  <span>Should stop</span>
                  <strong>{turnOverview.shouldStop}</strong>
                </div>
                <div className="runs-turn-overview-card">
                  <span>Planned</span>
                  <strong>{turnOverview.actionCount}</strong>
                </div>
                <div className="runs-turn-overview-card">
                  <span>LLM finish</span>
                  <strong>{turnOverview.finishReason}</strong>
                </div>
                <div className="runs-turn-overview-card">
                  <span>Time</span>
                  <strong>{turnOverview.createdAt}</strong>
                </div>
                <div className="runs-turn-overview-card">
                  <span>Errors</span>
                  <strong>{turnOverview.errorCount}</strong>
                </div>
              </div>
              <p className="runs-detail-summary">
                {selectedTurn?.decision_step?.summary || selectedRun?.reasoning_summary || "No decision summary available."}
              </p>
            </section>

            <section className="runs-detail-section">
              <div className="runs-detail-title">
                <strong>Prompt</strong>
                <span>llm_prompt</span>
              </div>
              <button
                type="button"
                className={`runs-collapse-toggle${promptOpen ? " is-open" : ""}`}
                onClick={() => setPromptOpen((current) => !current)}
              >
                <strong>{promptOpen ? "Hide prompt" : "Show prompt"}</strong>
                <span>{promptLines.length} lines</span>
              </button>
              {promptOpen ? (
                <div className="runs-code-block">
                  {promptLines.map((line, index) => (
                    <span key={`${index}-${line}`}>{line}</span>
                  ))}
                </div>
              ) : null}
            </section>

            <section className="runs-detail-section">
              <div className="runs-detail-title">
                <strong>Response</strong>
                <span>llm_response</span>
              </div>
              <button
                type="button"
                className={`runs-collapse-toggle${responseOpen ? " is-open" : ""}`}
                onClick={() => setResponseOpen((current) => !current)}
              >
                <strong>{responseOpen ? "Hide response" : "Show response"}</strong>
                <span>{responseLines.length} lines</span>
              </button>
              {responseOpen ? (
                <div className="runs-code-block is-soft">
                  {responseLines.map((line, index) => (
                    <span key={`${index}-${line}`}>{line}</span>
                  ))}
                </div>
              ) : null}
            </section>

            <section className="runs-detail-section">
              <div className="runs-detail-title">
                <strong>Artifacts</strong>
                <span>{artifactRows.length}</span>
              </div>
              <div className="runs-artifact-list">
                {artifactRows.map((artifact: RuntimeRunArtifactResponse) => (
                  <div key={artifact.artifact_id} className="runs-artifact-card">
                    <button
                      type="button"
                      className={`runs-artifact-row${expandedArtifactId === artifact.artifact_id ? " is-expanded" : ""}`}
                      onClick={() =>
                        setExpandedArtifactId((current) => (current === artifact.artifact_id ? "" : artifact.artifact_id))
                      }
                    >
                      <strong>{artifact.title || artifact.artifact_type}</strong>
                      <code>{artifact.artifact_type}</code>
                    </button>
                    {expandedArtifactId === artifact.artifact_id ? (
                      <div className="runs-code-block is-soft runs-artifact-detail">
                        {JSON.stringify(artifact.content, null, 2)
                          .split("\n")
                          .map((line, index) => (
                            <span key={`${artifact.artifact_id}-${index}`}>{line}</span>
                          ))}
                      </div>
                    ) : null}
                  </div>
                ))}
                {artifactRows.length === 0 ? <div className="runs-empty-state">No artifacts for this turn.</div> : null}
              </div>
            </section>
          </div>
        </article>
      </section>
    </div>
  );
}
