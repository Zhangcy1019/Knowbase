import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import "./runs.css";
import { IconTraceDetail, IconTraceFocus, IconTraceList, IconTraceLoop } from "../../shared/icons";
import {
  getRuntimeRunTrace,
  listRuntimeRuns,
  type RuntimeRunArtifactResponse,
  type RuntimeRunSummary,
  type RuntimeTraceReplayResponse,
  type RuntimeTraceTurnResponse,
} from "../../shared/api";

function PanelMark({ children }: { children: ReactNode }) {
  return <span className="runs-panel-mark">{children}</span>;
}

function formatTime(value: string | null) {
  if (!value) {
    return "--";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatStatus(status: string, requiresReview: boolean) {
  if (requiresReview) {
    return "review";
  }
  return status || "unknown";
}

function buildPromptLines(turn: RuntimeTraceTurnResponse | null) {
  const payload = turn?.llm_prompt_artifact?.content?.prompt;
  if (typeof payload !== "string" || !payload.trim()) {
    return ["No prompt artifact available."];
  }
  return payload.split("\n").filter((line) => line.length > 0);
}

function buildResponseLines(turn: RuntimeTraceTurnResponse | null) {
  const artifactContent = turn?.llm_response_artifact?.content;
  if (!artifactContent) {
    return ["No response artifact available."];
  }
  return JSON.stringify(artifactContent, null, 2).split("\n");
}

function summarizeTurn(turn: RuntimeTraceTurnResponse, index: number) {
  const step = turn.decision_step;
  if (step?.summary) {
    return step.summary;
  }
  if (turn.action_steps[0]?.summary) {
    return turn.action_steps[0].summary;
  }
  return `Turn ${index + 1}`;
}

export function RunsPage({ activePartition }: { activePartition: string | null }) {
  const [runs, setRuns] = useState<RuntimeRunSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [trace, setTrace] = useState<RuntimeTraceReplayResponse | null>(null);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [loadingTrace, setLoadingTrace] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

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
    listRuntimeRuns(activePartition)
      .then((items) => {
        if (cancelled) {
          return;
        }
        setRuns(items);
        setSelectedRunId(items[0]?.run_id ?? "");
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
      return () => {
        cancelled = true;
      };
    }
    setLoadingTrace(true);
    getRuntimeRunTrace(selectedRunId)
      .then((payload) => {
        if (!cancelled) {
          setTrace(payload);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setTrace(null);
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

  const selectedRun = useMemo(
    () => runs.find((item) => item.run_id === selectedRunId) ?? null,
    [runs, selectedRunId],
  );
  const turns = trace?.turns ?? [];
  const selectedTurn = turns[0] ?? null;
  const promptLines = buildPromptLines(selectedTurn);
  const responseLines = buildResponseLines(selectedTurn);
  const artifactRows = trace?.artifacts ?? [];
  const reviewCount = runs.filter((item) => item.requires_review).length;

  return (
    <section className="runs-page">
      <header className="runs-page-header">
        <div className="runs-page-copy">
          <h2>Runs</h2>
        </div>
        <div className="runs-page-status">
          <span className="runs-page-pill">{runs.length}</span>
          <span className="runs-page-pill is-accent">{reviewCount}</span>
        </div>
      </header>

      <section className="runs-workbench">
        <article className="skeleton-card runs-rail-card">
          <div className="runs-panel-head">
            <div className="runs-panel-heading">
              <PanelMark>
                <IconTraceList />
              </PanelMark>
              <h3>List</h3>
            </div>
          </div>

          <div className="runs-filter-strip">
            <span className="runs-chip is-active">{activePartition || "No active partition"}</span>
            <span className="runs-chip">All</span>
            <span className="runs-chip">Review {reviewCount}</span>
          </div>

          <div className="runs-list-scroll">
            <div className="runs-list">
              {!activePartition ? <div className="runs-empty-state">Select or create a partition first.</div> : null}
              {loadingRuns ? <div className="runs-empty-state">Loading runs...</div> : null}
              {!loadingRuns && errorMessage ? <div className="runs-empty-state">{errorMessage}</div> : null}
              {!activePartition ? null : !loadingRuns && !errorMessage && runs.length === 0 ? (
                <div className="runs-empty-state">No runs for the active partition.</div>
              ) : null}
              {runs.map((run) => (
                <button
                  key={run.run_id}
                  type="button"
                  className={`runs-row${run.run_id === selectedRunId ? " is-active" : ""}`}
                  onClick={() => setSelectedRunId(run.run_id)}
                >
                  <div className="runs-row-top">
                    <strong>{run.run_id}</strong>
                    <span className={`runs-inline-status is-${formatStatus(run.status, run.requires_review)}`}>
                      {formatStatus(run.status, run.requires_review)}
                    </span>
                  </div>
                  <p>{run.objective || run.reasoning_summary || "No objective available."}</p>
                  <div className="runs-row-meta">
                    <span>{run.partition}</span>
                    <span>{run.source_type}</span>
                    <span>{run.step_count} step</span>
                    <span>{formatTime(run.created_at)}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </article>

        <div className="runs-center-stack">
          <article className="skeleton-card runs-summary-card">
            <div className="runs-panel-head">
              <div className="runs-panel-heading">
                <PanelMark>
                  <IconTraceFocus />
                </PanelMark>
                <h3>{selectedRun?.run_id || "No run"}</h3>
              </div>
              <code>{selectedRun?.partition || activePartition || "No active partition"}</code>
            </div>

            <div className="runs-summary-grid">
              <div className="runs-summary-hero">
                <strong>
                  {selectedRun?.objective || selectedRun?.reasoning_summary || "Select a run to inspect trace details."}
                </strong>
              </div>

              <div className="runs-summary-stats">
                <div className="runs-stat-card">
                  <span>Status</span>
                  <strong>{selectedRun ? formatStatus(selectedRun.status, selectedRun.requires_review) : "--"}</strong>
                </div>
                <div className="runs-stat-card">
                  <span>Turns</span>
                  <strong>{turns.length}</strong>
                </div>
                <div className="runs-stat-card">
                  <span>Artifacts</span>
                  <strong>{artifactRows.length}</strong>
                </div>
                <div className="runs-stat-card">
                  <span>Actions</span>
                  <strong>{trace?.run.actions.length ?? 0}</strong>
                </div>
              </div>
            </div>
          </article>

          <article className="skeleton-card runs-turn-card">
            <div className="runs-panel-head">
              <div className="runs-panel-heading">
                <PanelMark>
                  <IconTraceLoop />
                </PanelMark>
                <h3>Turns</h3>
              </div>
            </div>

            <div className="runs-turn-scroll">
              <div className="runs-turn-list">
                {loadingTrace ? <div className="runs-empty-state">Loading trace...</div> : null}
                {!loadingTrace && !trace ? <div className="runs-empty-state">No trace loaded.</div> : null}
                {turns.map((turn, index) => (
                  <button key={`${turn.turn_index}`} type="button" className={`runs-turn-row${index === 0 ? " is-active" : ""}`}>
                    <div className="runs-turn-marker" />
                    <div className="runs-turn-body">
                      <div className="runs-turn-head">
                        <strong>{String(turn.turn_index).padStart(2, "0")}</strong>
                        <span>{turn.decision_step?.step_type || "turn"}</span>
                      </div>
                      <p>{summarizeTurn(turn, index)}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </article>
        </div>

        <article className="skeleton-card runs-detail-card">
          <div className="runs-panel-head">
            <div className="runs-panel-heading">
              <PanelMark>
                <IconTraceDetail />
              </PanelMark>
              <h3>Turn 01</h3>
            </div>
          </div>

          <div className="runs-detail-scroll">
            <section className="runs-detail-section">
              <div className="runs-detail-title">
                <strong>Decision</strong>
                <span>{selectedTurn?.decision_artifact?.artifact_type || "decision"}</span>
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
              <div className="runs-code-block">
                {promptLines.map((line) => (
                  <span key={line}>{line}</span>
                ))}
              </div>
            </section>

            <section className="runs-detail-section">
              <div className="runs-detail-title">
                <strong>Response</strong>
                <span>llm_response</span>
              </div>
              <div className="runs-code-block is-soft">
                {responseLines.map((line) => (
                  <span key={line}>{line}</span>
                ))}
              </div>
            </section>

            <section className="runs-detail-section">
              <div className="runs-detail-title">
                <strong>Artifacts</strong>
                <span>{artifactRows.length}</span>
              </div>
              <div className="runs-artifact-list">
                {artifactRows.map((artifact: RuntimeRunArtifactResponse) => (
                  <div key={artifact.artifact_id} className="runs-artifact-row">
                    <strong>{artifact.title || artifact.artifact_type}</strong>
                    <code>{artifact.artifact_type}</code>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </article>
      </section>
    </section>
  );
}
