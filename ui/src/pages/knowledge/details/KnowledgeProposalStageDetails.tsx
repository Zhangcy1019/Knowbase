import type { ReactNode } from "react";

import { KnowledgeRecordTree } from "../KnowledgeRecordTree";
import { effectiveStageStatus } from "../stageStatus";

type KnowledgeProposalStageDetailsProps = {
  payload: unknown;
  mode: "summary" | "details";
};

type AnyRecord = Record<string, unknown>;

function asRecord(value: unknown): AnyRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? value as AnyRecord : {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function text(value: unknown, fallback = "--") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function tone(status: string) {
  if (["proposed", "no_change", "completed"].includes(status)) return "good";
  if (["blocked", "requires_review"].includes(status)) return "review";
  if (status === "failed") return "failed";
  return "";
}

function Metric({ label, value, variant = "" }: { label: string; value: string; variant?: string }) {
  return (
    <div className={`knowledge-detail-metric${variant ? ` is-${variant}` : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="knowledge-detail-section">
      <h4>{title}</h4>
      {children}
    </section>
  );
}

function ProposalAlgorithm() {
  return (
    <div className="knowledge-proposal-algorithms">
      <article>
        <strong>Promote semantic keys</strong>
        <p>Suggest a new facet key when it is absent from the schema and appears in at least 30% of statistics cases, with a minimum support of 2.</p>
      </article>
      <article>
        <strong>Demote unused facet keys</strong>
        <p>Suggest removal when an existing key was not touched by this batch and has zero semantic-index and facet-index support.</p>
      </article>
      <article>
        <strong>Review affected keys</strong>
        <p>Suggest re-evaluation when an existing key is touched and the evidence contains missing signals or stable key gaps.</p>
      </article>
    </div>
  );
}

export function KnowledgeProposalStageDetails({ payload, mode }: KnowledgeProposalStageDetailsProps) {
  const record = asRecord(payload);
  const stage = asRecord(record.stage || record);
  const output = asRecord(stage.output);
  const proposal = asRecord(output.proposal);
  const diagnostics = asArray(output.diagnostics);
  const conflicts = asArray(output.conflicts);
  const impact = asRecord(output.impact);
  const status = effectiveStageStatus("Proposal", record);
  const newKeys = asArray(proposal.suggested_new_keys);
  const updatedKeys = asArray(proposal.suggested_updated_keys);
  const removedKeys = asArray(proposal.suggested_removed_keys);
  const candidateCount = newKeys.length + updatedKeys.length + removedKeys.length;
  const blocked = status === "blocked" || conflicts.length > 0;

  return (
    <>
      <div className="knowledge-detail-metrics">
        <Metric label="Proposal status" value={status} variant={tone(status)} />
        <Metric label="Candidate changes" value={String(candidateCount)} variant={candidateCount ? "review" : "good"} />
        <Metric label="Plugins evaluated" value={String(diagnostics.length)} />
        <Metric label="Conflicts" value={String(conflicts.length)} variant={conflicts.length ? "review" : "good"} />
      </div>

      <div className="knowledge-summary-grid">
        <section className={`knowledge-summary-block${blocked ? " is-warning" : ""}`}>
          <span>Decision basis</span>
          <strong>{status === "blocked" ? "Proposal was blocked" : candidateCount ? `${candidateCount} candidate schema change(s)` : "No schema change detected"}</strong>
          <p>{text(proposal.rationale, "Candidates are evidence-based suggestions and are not applied at this stage.")}</p>
        </section>
        <section className="knowledge-summary-block">
          <span>Projected impact</span>
          <strong>{text(impact.schema_change_count, "0")} schema key change(s)</strong>
          <p>{text(impact.affected_case_count, "0")} affected case(s); value proposals: {text(impact.value_proposal_count, "0")}.</p>
        </section>
      </div>

      <Section title="How proposal is produced">
        <ProposalAlgorithm />
        <p className="knowledge-detail-note">If Preparation reports inconsistent or stale evidence, the pipeline stops before plugins run. Otherwise it runs every enabled plugin, merges duplicate keys, preserves plugin evidence, and records conflicts instead of silently choosing between incompatible actions.</p>
      </Section>

      <Section title="Candidate changes">
        <div className="knowledge-proposal-candidate-groups">
          <div><span>New keys</span><strong>{newKeys.length ? newKeys.join(", ") : "None"}</strong></div>
          <div><span>Updated keys</span><strong>{updatedKeys.length ? updatedKeys.join(", ") : "None"}</strong></div>
          <div><span>Removed keys</span><strong>{removedKeys.length ? removedKeys.join(", ") : "None"}</strong></div>
        </div>
      </Section>

      {conflicts.length ? (
        <Section title="Conflicts requiring resolution">
          <div className="knowledge-reason-list">
            {conflicts.map((conflict, index) => {
              const item = asRecord(conflict);
              return (
                <div className="knowledge-reason-item" key={index}>
                  <div className="knowledge-reason-item-head">
                    <strong>{text(item.key, "Schema key conflict")}</strong>
                    <span>conflict</span>
                  </div>
                  <p>{text(item.reason, "Multiple plugins proposed incompatible actions.")}</p>
                  <p>Actions: {asArray(item.candidates).map((candidate) => text(candidate)).join(", ") || "--"}</p>
                </div>
              );
            })}
          </div>
        </Section>
      ) : null}

      {mode === "details" ? (
        <>
          <Section title="Plugin results">
            {diagnostics.length ? <KnowledgeRecordTree value={diagnostics} /> : <p className="knowledge-detail-note">No plugin diagnostics were recorded.</p>}
          </Section>
          <Section title="Structured proposal record">
            <KnowledgeRecordTree value={payload} />
          </Section>
        </>
      ) : (
        <p className="knowledge-detail-note">Switch to full record to inspect each plugin result, evidence, and metric.</p>
      )}
    </>
  );
}
