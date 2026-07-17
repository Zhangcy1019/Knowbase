import type { ReactNode } from "react";

import "./runs.css";
import { IconTraceDetail, IconTraceFocus, IconTraceList, IconTraceLoop } from "../../shared/icons";

const runRows = [
  {
    id: "RUN-2417",
    partition: "Claims",
    status: "completed",
    source: "backlog",
    turns: 1,
    startedAt: "09:42",
    objective: "Review backlog batch BATCH-08 and summarize next maintenance work.",
  },
  {
    id: "RUN-2416",
    partition: "Tax",
    status: "completed",
    source: "manual",
    turns: 1,
    startedAt: "09:18",
    objective: "Inspect pending update wave and respond with a traceable summary.",
  },
  {
    id: "RUN-2415",
    partition: "Policy",
    status: "review",
    source: "backlog",
    turns: 2,
    startedAt: "08:57",
    objective: "Compare affected cases and decide whether follow-up rebuild is needed.",
  },
  {
    id: "RUN-2414",
    partition: "Audit",
    status: "failed",
    source: "scheduled",
    turns: 1,
    startedAt: "08:11",
    objective: "Check runtime batch readiness and explain why execution could not continue.",
  },
];

const turnRows = [
  { id: "01", mode: "Decision", summary: "Responded with a compact batch analysis and stopped.", status: "selected" },
  { id: "00", mode: "Request", summary: "Request loaded with batch summary and preparation notes.", status: "idle" },
];

const promptLines = [
  "Analyze backlog batch BATCH-08 for partition Claims.",
  "Current runtime mode is analysis-only.",
  "Do not propose any tool_call or skill_call actions.",
  "Return one respond action or stop immediately.",
];

const responseLines = [
  "{",
  '  "reasoning_summary": "Batch BATCH-08 contains six recent case updates.",',
  '  "action_plan_summary": "Respond with a short maintenance summary and stop.",',
  '  "should_stop": true,',
  '  "actions": [{ "kind": "respond", "summary": "Batch summarized for operator review." }]',
  "}",
];

const artifactRows = [
  { label: "Request", type: "runtime_request" },
  { label: "Context", type: "planner_context" },
  { label: "Prompt", type: "llm_prompt" },
  { label: "Response", type: "llm_response" },
];

function PanelMark({ children }: { children: ReactNode }) {
  return <span className="runs-panel-mark">{children}</span>;
}

export function RunsPage() {
  return (
    <section className="runs-page">
      <header className="runs-page-header">
        <div className="runs-page-copy">
          <h2>Runs</h2>
        </div>
        <div className="runs-page-status">
          <span className="runs-page-pill">24</span>
          <span className="runs-page-pill is-accent">3</span>
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
            <span className="runs-chip is-active">All</span>
            <span className="runs-chip">Backlog</span>
            <span className="runs-chip">Needs review</span>
            <span className="runs-chip">Failed</span>
          </div>

          <div className="runs-list-scroll">
            <div className="runs-list">
              {runRows.map((run, index) => (
                <button key={run.id} type="button" className={`runs-row${index === 0 ? " is-active" : ""}`}>
                  <div className="runs-row-top">
                    <strong>{run.id}</strong>
                    <span className={`runs-inline-status is-${run.status}`}>{run.status}</span>
                  </div>
                  <p>{run.objective}</p>
                  <div className="runs-row-meta">
                    <span>{run.partition}</span>
                    <span>{run.source}</span>
                    <span>{run.turns} turn</span>
                    <span>{run.startedAt}</span>
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
                <h3>RUN-2417</h3>
              </div>
              <code>Claims</code>
            </div>

            <div className="runs-summary-grid">
              <div className="runs-summary-hero">
                <strong>Review backlog batch BATCH-08 and summarize next maintenance work.</strong>
              </div>

              <div className="runs-summary-stats">
                <div className="runs-stat-card">
                  <span>Status</span>
                  <strong>Completed</strong>
                </div>
                <div className="runs-stat-card">
                  <span>Turns</span>
                  <strong>1</strong>
                </div>
                <div className="runs-stat-card">
                  <span>Artifacts</span>
                  <strong>4</strong>
                </div>
                <div className="runs-stat-card">
                  <span>Actions</span>
                  <strong>1</strong>
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
                {turnRows.map((turn) => (
                  <button key={turn.id} type="button" className={`runs-turn-row${turn.status === "selected" ? " is-active" : ""}`}>
                    <div className="runs-turn-marker" />
                    <div className="runs-turn-body">
                      <div className="runs-turn-head">
                        <strong>{turn.id}</strong>
                        <span>{turn.mode}</span>
                      </div>
                      <p>{turn.summary}</p>
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
                <span>respond + stop</span>
              </div>
              <p className="runs-detail-summary">Batch BATCH-08 contains six recent case updates.</p>
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
                <span>4</span>
              </div>
              <div className="runs-artifact-list">
                {artifactRows.map((artifact) => (
                  <div key={artifact.label} className="runs-artifact-row">
                    <strong>{artifact.label}</strong>
                    <code>{artifact.type}</code>
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
