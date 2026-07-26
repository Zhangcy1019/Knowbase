import type { ReactNode } from "react";
import { useState } from "react";
import { useEffect } from "react";

import { IconBacklog, IconPartition, IconTraceDetail, IconTraceLoop } from "../../shared/icons";
import {
  getKnowledgeDrain,
  getKnowledgeOverview,
  listKnowledgeDrains,
  type KnowledgeDrainDetail,
  type KnowledgeDrainSummary,
  type KnowledgeOverview,
} from "../../shared/api";

import { KnowledgeAuditRuntimeCard } from "./KnowledgeAuditRuntimeCard";
import { KnowledgeDecisionCard } from "./KnowledgeDecisionCard";
import { KnowledgeMutationPlanCard } from "./KnowledgeMutationPlanCard";
import { KnowledgePatchDiffCard } from "./KnowledgePatchDiffCard";
import { KnowledgeDetailModal } from "./KnowledgeDetailModal";
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

  const selectedSummary = selectedDrain || drainRuns[0] || null;

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
            <span>Decision <strong>{selectedDrain?.governance_result ? "recorded" : "--"}</strong></span>
          </div>
          <div className="knowledge-selected-run-links">
            <a href="/backlog"><IconBacklog /><span>Batch</span><strong>{selectedSummary?.batch_id || "--"}</strong></a>
            <span><IconTraceLoop /><span>Mutation plan</span><strong>{selectedDrain?.mutation_plan_id || "--"}</strong></span>
            <a href="/partition"><IconPartition /><span>Revision</span><strong>{selectedSummary?.applied_revision || selectedSummary?.base_revision || "pending"}</strong></a>
          </div>
          <div className="knowledge-process-list">
            <KnowledgeDecisionCard onOpen={openDebugSection} payload={selectedDrain?.governance_result} />
            <KnowledgeMutationPlanCard onOpen={openDebugSection} payload={selectedDrain?.mutation_plan} />
            <KnowledgePatchDiffCard onOpen={openDebugSection} payload={selectedDrain} />
            <KnowledgeAuditRuntimeCard onOpen={openDebugSection} payload={selectedDrain} />
          </div>
        </article>
      </section>

      {selectedDebugSection ? (
        <KnowledgeDetailModal
          title={selectedDebugSection.title}
          description={selectedDebugSection.description}
          payload={selectedDebugSection.payload}
          onClose={() => setSelectedDebugSection(null)}
        />
      ) : null}
    </section>
  );
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
