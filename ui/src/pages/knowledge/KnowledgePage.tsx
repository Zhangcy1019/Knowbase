import type { ReactNode } from "react";
import { useState } from "react";
import { useEffect } from "react";

import { IconBacklog, IconPartition, IconTraceDetail, IconTraceLoop } from "../../shared/icons";
import {
  getKnowledgeDrain,
  getKnowledgeOverview,
  listKnowledgeDrains,
  reviewKnowledgeDrain,
  type KnowledgeDrainDetail,
  type KnowledgeDrainSummary,
  type KnowledgeOverview,
} from "../../shared/api";

import { KnowledgeFlowCard, type KnowledgeFlowMetric } from "./KnowledgeFlowCard";
import { KnowledgeDetailModal } from "./KnowledgeDetailModal";
import { effectiveStageStatus } from "./stageStatus";
import "./knowledge.css";

function PanelMark({ children }: { children: ReactNode }) {
  return <span className="knowledge-panel-mark">{children}</span>;
}

export function KnowledgePage({ activePartition }: { activePartition: string | null }) {
  const [drainRuns, setDrainRuns] = useState<KnowledgeDrainSummary[]>([]);
  const [selectedDrain, setSelectedDrain] = useState<KnowledgeDrainDetail | null>(null);
  const [overview, setOverview] = useState<KnowledgeOverview | null>(null);
  const [loadError, setLoadError] = useState("");
  const [selectedDebugSection, setSelectedDebugSection] = useState<{
    title: string;
    description: string;
    payload: unknown;
  } | null>(null);
  const openDebugSection = (title: string, description: string, payload: unknown) => {
    setSelectedDebugSection({ title, description, payload });
  };

  useEffect(() => {
    if (!activePartition) {
      setDrainRuns([]);
      setSelectedDrain(null);
      setOverview(null);
      return;
    }
    let cancelled = false;
    setLoadError("");
    Promise.all([listKnowledgeDrains(activePartition), getKnowledgeOverview(activePartition)])
      .then(([drains, currentOverview]) => {
        if (cancelled) return;
        setDrainRuns(drains);
        setOverview(currentOverview);
        if (drains.length > 0) {
          return getKnowledgeDrain(drains[0].decision_id).then((detail) => {
            if (!cancelled) setSelectedDrain(detail);
          });
        }
        setSelectedDrain(null);
        return undefined;
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setLoadError(error instanceof Error ? error.message : "Knowledge data unavailable");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [activePartition]);

  const selectDrain = (run: KnowledgeDrainSummary) => {
    setLoadError("");
    getKnowledgeDrain(run.decision_id)
      .then(setSelectedDrain)
      .catch((error: unknown) => setLoadError(error instanceof Error ? error.message : "Drain detail unavailable"));
  };

  const reviewSelectedDrain = async (action: "approve" | "discard" | "retry") => {
    if (!selectedDrain) return;
    const updated = await reviewKnowledgeDrain(selectedDrain.decision_id, action);
    setSelectedDrain(updated);
    const [drains, currentOverview] = await Promise.all([
      listKnowledgeDrains(activePartition || ""),
      getKnowledgeOverview(activePartition || ""),
    ]);
    setDrainRuns(drains);
    setOverview(currentOverview);
  };

  const selectedSummary = selectedDrain || drainRuns[0] || null;
  const flowCards = selectedDrain ? buildFlowCards(selectedDrain) : [];

  return (
    <section className="knowledge-page">
      <header className="knowledge-page-header">
        <div className="knowledge-page-copy">
          <div className="knowledge-title-line">
            <h2>Knowledge</h2>
          </div>
        </div>
        <code>{activePartition || "No active partition"}</code>
      </header>

      <section className="knowledge-overview-strip">
        <span className="knowledge-overview-label">Knowledge snapshot</span>
        <div><span>Cases</span><strong>{overview?.case_count ?? "--"}</strong></div>
        <div><span>Facet keys</span><strong>{overview?.facet_key_count ?? "--"}</strong></div>
        <div><span>Pending review</span><strong>{overview?.pending_decision_count ?? "--"}</strong></div>
        <div><span>Last drain</span><strong>{formatDate(overview?.last_drain_at)}</strong></div>
      </section>

      {loadError ? <div className="knowledge-load-error">{loadError}</div> : null}

      <section className="knowledge-run-workbench">
        <article className="skeleton-card knowledge-run-list-card">
          <div className="knowledge-panel-head">
            <div className="knowledge-panel-heading">
              <PanelMark><IconTraceLoop /></PanelMark>
              <h3>Drain Runs</h3>
            </div>
            <span className="knowledge-inline-note">{drainRuns.length}</span>
          </div>
          <div className="knowledge-run-list">
            {drainRuns.map((run) => (
              <button
                key={run.decision_id}
                type="button"
                className={"knowledge-run-item" + (selectedSummary?.decision_id === run.decision_id ? " is-active" : "")}
                onClick={() => selectDrain(run)}
              >
                <div className="knowledge-run-item-top">
                  <strong>{run.decision_id}</strong>
                  <span className={"knowledge-status is-" + statusClass(run.status)}>{run.status}</span>
                </div>
                <div className="knowledge-run-item-meta">
                  <span>{formatDate(run.created_at)}</span>
                  <span>{run.change_count} changes</span>
                </div>
              </button>
            ))}
          </div>
        </article>

        <article className="skeleton-card knowledge-selected-run-card">
          <div className="knowledge-panel-head">
            <div className="knowledge-panel-heading">
              <PanelMark><IconTraceDetail /></PanelMark>
              <h3>Selected Drain</h3>
            </div>
            <code>{selectedSummary?.decision_id || "No drain selected"}</code>
          </div>
          <div className="knowledge-selected-run-meta">
            <span>Status <strong className="knowledge-accent-text">{selectedSummary?.status || "--"}</strong></span>
            <span>Batch <strong>{selectedSummary?.batch_id || "--"}</strong></span>
            <span>Decision <strong>{String(selectedDrain?.outcome?.outcome || "--")}</strong></span>
          </div>
          <div className="knowledge-selected-run-links">
            <a href="/backlog"><IconBacklog /><span>Batch</span><strong>{selectedSummary?.batch_id || "--"}</strong></a>
            <span><IconTraceLoop /><span>Mutation plan</span><strong>{selectedDrain?.mutation_plan_id || "--"}</strong></span>
            <a href="/partition"><IconPartition /><span>Revision</span><strong>{selectedSummary?.applied_revision || selectedSummary?.base_revision || "pending"}</strong></a>
          </div>
          <div className="knowledge-flow-list">
            {flowCards.map((card) => (
              <KnowledgeFlowCard
                key={card.title}
                index={card.index}
                title={card.title}
                kicker={card.kicker}
                status={card.status}
                tone={card.tone}
                summary={card.summary}
                method={card.method}
                metrics={card.metrics}
                onOpen={() => openDebugSection(card.title, card.description, card.payload)}
              />
            ))}
          </div>
        </article>
      </section>

      {selectedDebugSection ? (
        <KnowledgeDetailModal
          title={selectedDebugSection.title}
          description={selectedDebugSection.description}
          payload={selectedDebugSection.payload}
          onClose={() => setSelectedDebugSection(null)}
          onReviewAction={selectedDebugSection.title === "Outcome" ? reviewSelectedDrain : undefined}
        />
      ) : null}
    </section>
  );
}

function asRecord(value: unknown): Record<string, any> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, any>
    : {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

type FlowCardData = {
  index: string;
  title: string;
  kicker: string;
  status: string;
  tone: "good" | "review" | "failed" | "idle";
  summary: string;
  method?: string;
  metrics: KnowledgeFlowMetric[];
  description: string;
  payload: unknown;
};

const stageOrder = [
  ["preparation", "Preparation", "Evidence preparation"],
  ["proposal", "Proposal", "Schema proposal"],
  ["runtime", "Runtime", "Read-only analysis"],
  ["projection", "Projection", "Case impact projection"],
  ["mutation_plan", "Mutation Plan", "Auditable write plan"],
  ["apply", "Apply", "Workspace mutation"],
] as const;

function buildFlowCards(detail: KnowledgeDrainDetail): FlowCardData[] {
  const input = asRecord(detail.input);
  const statistics = asRecord(input.statistics_snapshot);
  const workingSet = asRecord(input.working_set);
  const cards: FlowCardData[] = [
    {
      index: "01",
      title: "Input",
      kicker: "Drain boundary",
      status: "recorded",
      tone: "good",
      summary: "The evidence used by this drain was frozen before analysis started.",
      metrics: [
        { label: "Base revision", value: shortValue(input.base_revision) },
        { label: "Cases", value: countValue(statistics.case_count ?? workingSet.case_count) },
        { label: "Statistics", value: input.statistics_fingerprint ? "fingerprinted" : "not recorded" },
      ],
      description: "Input records the revision, statistics snapshot, and working set that every later stage must use.",
      payload: input,
    },
  ];

  stageOrder.forEach(([key, title, kicker], index) => {
    const stage = key === "mutation_plan"
      ? asRecord(detail.stages[key] || asRecord(detail.execution).plan)
      : key === "apply"
        ? asRecord(detail.stages[key] || detail.execution)
        : asRecord(detail.stages[key]);
    const output = title === "Mutation Plan" || title === "Apply"
      ? asRecord(stage.output || stage)
      : asRecord(stage.output);
    const exists = Object.keys(stage).length > 0;
    const status = exists ? effectiveStageStatus(title, stage, key === "apply" ? detail.status : "recorded") : "not run";
    const tone = statusTone(status);
    cards.push({
      index: String(index + 2).padStart(2, "0"),
      title,
      kicker,
      status,
      tone,
      summary: stageSummary(title, status, output, stage),
      method: title === "Preparation" ? preparationCoverageMethod() : undefined,
      metrics: stageMetrics(title, output, stage, detail),
      description: stageDescription(title),
      payload: exists
        ? {
          stage,
          input: asRecord(stage.input),
          execution: detail.execution,
          ...(title === "Runtime" ? { runtime_run_id: detail.runtime_run_id } : {}),
        }
        : {
          status: "not_run",
          stage: null,
          ...(title === "Runtime" ? { runtime_run_id: detail.runtime_run_id } : {}),
        },
    });
  });

  const outcome = asRecord(detail.outcome);
  const reasons = asArray(outcome.reasons);
  const finalStatus = textValue(detail.status, "unknown");
  cards.push({
    index: String(cards.length + 1).padStart(2, "0"),
    title: "Outcome",
    kicker: "Drain decision",
    status: textValue(outcome.outcome, finalStatus),
    tone: statusTone(textValue(outcome.outcome, finalStatus)),
    summary: reasons.length ? textValue(reasons[0]) : outcomeSummary(finalStatus),
    metrics: [
      { label: "Final status", value: finalStatus },
      { label: "Outcome", value: textValue(outcome.outcome) },
      { label: "Transitions", value: String(asArray(detail.status_history).length) },
    ],
    description: "Outcome is the final governance result, including reasons, review state, and status transitions.",
    payload: {
      decision_id: detail.decision_id,
      outcome,
      status_history: detail.status_history,
      reviewer: detail.reviewer,
      review_reason: detail.review_reason,
    },
  });
  return cards;
}

function stageSummary(title: string, status: string, output: Record<string, any>, stage: Record<string, any>) {
  if (status === "not run") return `${title} was not reached in this drain.`;
  if (stage.error) return textValue(stage.error);
  if (title === "Projection" && status === "passed") return "Projection ran successfully; every target case already matches the accepted schema.";
  if (title === "Projection" && status === "no_action") return "Projection had no target cases to evaluate.";
  if (title === "Mutation Plan" && status === "no_action") return "No mutation action was required because projection produced no changes.";
  if (title === "Apply" && status === "passed") return "Apply checked the plan and found no workspace changes to write.";
  if (title === "Proposal" && status === "no_action") return "All proposal plugins ran; none produced an actionable schema change.";
  if (title === "Preparation") return `Evidence ${textValue(output.consistency_status, "was checked")}; coverage ${percentage(output.coverage)}.`;
  if (title === "Proposal") return `Schema proposal ${textValue(output.status, status)} with ${proposalCount(output)} candidate change(s).`;
  if (title === "Runtime") return output.metadata ? "Read-only runtime analysis was recorded." : "Runtime analysis was recorded.";
  if (title === "Projection") return `Projected ${countValue(output.estimated_change_count ?? output.changed_case_count)} case change(s).`;
  if (title === "Mutation Plan") return output.plan_id ? `Plan ${shortValue(output.plan_id)} is available for audit.` : "A mutation plan was recorded.";
  if (title === "Apply") return output.applied_revision ? `Workspace committed at ${shortValue(output.applied_revision)}.` : "No workspace mutation was applied.";
  return `${title} completed.`;
}

function preparationCoverageMethod() {
  return "100% - 10% per missing signal (max 40%) - 5% per uncovered existing key (max 30%) - 20% for sampled cases with no semantic keys; minimum 0%.";
}

function stageMetrics(title: string, output: Record<string, any>, stage: Record<string, any>, detail: KnowledgeDrainDetail): KnowledgeFlowMetric[] {
  if (textValue(stage.status, "not run") === "not run") return [{ label: "Execution", value: "Skipped" }];
  if (title === "Preparation") return [
    { label: "Coverage", value: percentage(output.coverage) },
    { label: "Consistency", value: textValue(output.consistency_status) },
    { label: "Mismatches", value: countValue(output.consistency_mismatches) },
  ];
  if (title === "Proposal") return [
    { label: "Status", value: textValue(output.status, textValue(stage.status)) },
    { label: "Candidates", value: String(proposalCount(output)) },
    { label: "Conflicts", value: countValue(output.conflicts) },
  ];
  if (title === "Runtime") return [
    { label: "Mode", value: "Read-only" },
    { label: "Run", value: shortValue(asRecord(output.metadata).run_id) },
    { label: "Status", value: textValue(asRecord(output.metadata).runtime_status, textValue(stage.status)) },
  ];
  if (title === "Projection") return [
    { label: "Changed cases", value: countValue(output.changed_case_count ?? output.changes) },
    { label: "Unchanged", value: countValue(output.unchanged_case_count) },
    { label: "Estimated", value: countValue(output.estimated_change_count) },
  ];
  if (title === "Mutation Plan") return [
    { label: "Plan", value: shortValue(output.plan_id) },
    { label: "Case changes", value: countValue(output.case_changes) },
    { label: "Risk", value: textValue(output.risk_level) },
  ];
  if (title === "Apply") return [
    { label: "Paths", value: countValue(output.changed_paths ?? asRecord(detail.execution).changed_paths) },
    { label: "Cases", value: countValue(output.updated_case_ids ?? asRecord(detail.execution).updated_case_ids) },
    { label: "Revision", value: shortValue(output.applied_revision ?? asRecord(detail.execution).applied_revision) },
  ];
  return [{ label: "Status", value: textValue(stage.status) }];
}

function stageDescription(title: string) {
  return {
    Preparation: "Preparation joins the frozen statistics snapshot with the materialized indexes and checks whether the evidence is usable.",
    Proposal: "Proposal plugins compare the evidence against the current facet schema and produce candidate key/value changes.",
    Runtime: "Runtime is the read-only work phase. It may inspect cases and statistics, but it does not mutate the workspace.",
    Projection: "Projection translates an accepted schema direction into concrete case-level changes without writing files.",
    "Mutation Plan": "Mutation Plan packages the proposed file changes into an auditable write plan.",
    Apply: "Apply is the only stage allowed to change the partition workspace and create the resulting revision.",
  }[title] || `${title} details for this drain.`;
}

function proposalCount(output: Record<string, any>) {
  const proposal = asRecord(output.proposal || output);
  return asArray(proposal.suggested_new_keys).length
    + asArray(proposal.suggested_updated_keys).length
    + asArray(proposal.suggested_removed_keys).length
    + asArray(proposal.key_changes).length
    + asArray(proposal.value_changes).length;
}

function percentage(value: unknown) {
  const coverage = asRecord(value).coverage_score ?? value;
  if (coverage === undefined || coverage === null || coverage === "") return "--";
  const number = Number(coverage);
  return Number.isFinite(number) ? `${Math.round(number <= 1 ? number * 100 : number)}%` : textValue(coverage);
}

function countValue(value: unknown) {
  if (Array.isArray(value)) return String(value.length);
  if (typeof value === "number") return String(value);
  return value ? textValue(value) : "0";
}

function shortValue(value: unknown) {
  const result = textValue(value);
  return result.length > 18 ? `${result.slice(0, 8)}…${result.slice(-7)}` : result;
}

function textValue(value: unknown, fallback = "--") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function statusTone(status: string): FlowCardData["tone"] {
  if (["completed", "accepted", "applied", "recorded", "passed"].includes(status)) return "good";
  if (["failed", "stale", "rolled_back"].includes(status)) return "failed";
  if (["blocked", "requires_review", "applying", "retry_requested"].includes(status)) return "review";
  return "idle";
}

function outcomeSummary(status: string) {
  if (status === "completed" || status === "applied") return "The drain completed without a recorded blocking reason.";
  if (status === "requires_review") return "The drain is waiting for an explicit review decision.";
  if (status === "failed") return "The drain failed before the workflow could complete.";
  return `The drain ended with status ${status}.`;
}

function formatDate(value: string | null | undefined) {
  if (!value) return "--";
  return value.replace("T", " ").replace(/\.\d+Z$/, "").replace("Z", "");
}

function statusClass(status: string) {
  if (status === "requires_review") return "review";
  if (status === "failed" || status === "stale") return "failed";
  return "completed";
}
