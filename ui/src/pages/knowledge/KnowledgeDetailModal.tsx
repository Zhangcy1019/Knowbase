import type { ReactNode } from "react";
import { useEffect, useState } from "react";

import { KnowledgeApplyStageDetails } from "./details/KnowledgeApplyStageDetails";
import { KnowledgeInputStageDetails } from "./details/KnowledgeInputStageDetails";
import { KnowledgeMutationPlanStageDetails } from "./details/KnowledgeMutationPlanStageDetails";
import { KnowledgeOutcomeStageDetails } from "./details/KnowledgeOutcomeStageDetails";
import { KnowledgePreparationStageDetails } from "./details/KnowledgePreparationStageDetails";
import { KnowledgeProjectionStageDetails } from "./details/KnowledgeProjectionStageDetails";
import { KnowledgeProposalStageDetails } from "./details/KnowledgeProposalStageDetails";
import { KnowledgeRecordTree } from "./KnowledgeRecordTree";
import { KnowledgeRuntimeStageDetails } from "./details/KnowledgeRuntimeStageDetails";

type KnowledgeDetailModalProps = {
  title: string;
  description: string;
  payload: unknown;
  onClose: () => void;
  onReviewAction?: (action: "approve" | "discard" | "retry") => Promise<void>;
};

type AnyRecord = Record<string, unknown>;

function asRecord(value: unknown): AnyRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as AnyRecord) : {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function text(value: unknown, fallback = "--") {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  return fallback;
}

function Metric({ label, value, tone = "" }: { label: string; value: string; tone?: string }) {
  return (
    <div className={`knowledge-detail-metric${tone ? ` is-${tone}` : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function DetailSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="knowledge-detail-section">
      <h4>{title}</h4>
      {children}
    </section>
  );
}

function EmptyState({ children = "No data recorded." }: { children?: ReactNode }) {
  return <div className="knowledge-detail-empty">{children}</div>;
}

function SummaryBlock({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="knowledge-summary-block">
      <span>{title}</span>
      <div>{children}</div>
    </section>
  );
}

function reasonDetails(payload: AnyRecord) {
  return asArray(payload.reason_details).map(asRecord).filter((item) => item.message || item.reasons);
}

function ReasonDetails({ payload, compact = false }: { payload: AnyRecord; compact?: boolean }) {
  const details = reasonDetails(payload);
  if (!details.length) return null;
  const visible = compact ? details.slice(0, 2) : details;
  return (
    <DetailSection title={compact ? "Why" : "Decision trace"}>
      <div className="knowledge-reason-list">
        {visible.map((detail, index) => {
          const candidates = asRecord(detail.candidate_changes);
          const candidateText = [
            asArray(candidates.new_keys).length ? `${asArray(candidates.new_keys).length} new` : "",
            asArray(candidates.updated_keys).length ? `${asArray(candidates.updated_keys).length} updated` : "",
            asArray(candidates.removed_keys).length ? `${asArray(candidates.removed_keys).length} removed` : "",
          ].filter(Boolean).join(" · ");
          return (
            <article className="knowledge-reason-item" key={`${text(detail.code, "reason")}-${index}`}>
              <div className="knowledge-reason-item-head">
                <strong>{text(detail.message, "Governance rule evaluated")}</strong>
                <span>{text(detail.stage, "governance")}</span>
              </div>
              {candidateText ? <p>Proposed: {candidateText}</p> : null}
              {detail.root_cause ? <p><strong>Root cause:</strong> {text(detail.root_cause)}</p> : null}
              {asArray(detail.reasons).length ? <p>{asArray(detail.reasons).map((reason) => text(reason)).join(" · ")}</p> : null}
              {Object.keys(asRecord(detail.evidence)).length ? <p><strong>Evidence:</strong> {formatEvidence(detail.evidence)}</p> : null}
              {detail.next_action ? <p className="knowledge-reason-next">Next: {text(detail.next_action)}</p> : null}
            </article>
          );
        })}
      </div>
      {compact && details.length > visible.length ? <p className="knowledge-detail-note">More decision evidence is available in the full record.</p> : null}
    </DetailSection>
  );
}

function formatEvidence(value: unknown) {
  const record = asRecord(value);
  return Object.entries(record)
    .map(([key, item]) => `${fieldLabel(key)}=${formatEvidenceValue(item)}`)
    .join(" · ");
}

function fieldLabel(value: string) {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\s+/g, " ")
    .trim();
}

function formatEvidenceValue(value: unknown): string {
  if (Array.isArray(value)) return value.length ? value.map(formatEvidenceValue).join(", ") : "none";
  if (value && typeof value === "object") {
    return Object.entries(value as AnyRecord)
      .map(([key, item]) => `${key}:${formatEvidenceValue(item)}`)
      .join(", ");
  }
  return text(value, "none");
}

function summaryMetric(label: string, value: unknown, tone = "") {
  return <Metric label={label} value={text(value)} tone={tone} />;
}

function StageStrip({ stages }: { stages: AnyRecord }) {
  const stageNames = [
    ["preparation", "Preparation"],
    ["proposal", "Proposal"],
    ["runtime", "Runtime"],
    ["validation", "Validation"],
  ] as const;
  return (
    <div className="knowledge-stage-strip">
      {stageNames.map(([key, label]) => {
        const stage = asRecord(stages[key]);
        const status = text(stage.status, "not run");
        const tone = status === "completed" ? "good" : status === "blocked" || status === "failed" ? "review" : "";
        return (
          <div className={`knowledge-stage-chip${tone ? ` is-${tone}` : ""}`} key={key}>
            <span>{label}</span>
            <strong>{status}</strong>
          </div>
        );
      })}
    </div>
  );
}

function renderDecisionSummary(payload: AnyRecord) {
  const coverage = asRecord(payload.coverage);
  const proposal = asRecord(payload.proposal);
  const rebuild = asRecord(payload.rebuild);
  const newKeys = asArray(proposal.suggested_new_keys).length;
  const updatedKeys = asArray(proposal.suggested_updated_keys).length;
  const removedKeys = asArray(proposal.suggested_removed_keys).length;
  return (
    <>
      <div className="knowledge-detail-metrics">
        {summaryMetric("Decision", payload.decision, ["accepted", "no_change"].includes(payload.decision) ? "good" : "review")}
        {summaryMetric("Coverage", coverage.coverage_score === undefined ? "--" : `${Math.round(Number(coverage.coverage_score) * 100)}%`)}
        {summaryMetric("Schema changes", newKeys + updatedKeys + removedKeys)}
        {summaryMetric("Case rebuild", rebuild.estimated_change_count ?? rebuild.rebuild_scope ?? "None")}
      </div>
      <div className="knowledge-summary-grid">
        <SummaryBlock title="Outcome">
          <strong>{payload.requires_review ? "Manual review required" : text(payload.decision, "No decision")}</strong>
          <p>{payload.requires_review ? "The drain is waiting for a review decision." : "The governance result is ready for the next workflow step."}</p>
        </SummaryBlock>
        <SummaryBlock title="Proposed schema work">
          <strong>{newKeys + updatedKeys + removedKeys ? `${newKeys + updatedKeys + removedKeys} schema change(s)` : "No schema change"}</strong>
          <p>{newKeys} new · {updatedKeys} updated · {removedKeys} removed</p>
        </SummaryBlock>
      </div>
      <StageStrip stages={asRecord(payload.stages)} />
      {payload.consistency_status && payload.consistency_status !== "consistent" ? (
        <SummaryBlock title="Evidence state">
          <strong>{text(payload.consistency_status)}</strong>
          <p>Statistics and materialized indexes are not currently aligned.</p>
        </SummaryBlock>
      ) : null}
      <ReasonDetails payload={payload} compact />
    </>
  );
}

function renderPatchSummary(payload: AnyRecord) {
  const plan = asRecord(payload.mutation_plan);
  const changes = asArray(plan.case_changes);
  const changedPaths = asArray(payload.changed_paths);
  const hasPlan = Object.keys(plan).length > 0;
  const patchStatus = !hasPlan ? "Not generated" : payload.applied_revision ? "Applied" : "Not applied";
  return (
    <>
      <div className="knowledge-detail-metrics">
        {summaryMetric("Status", patchStatus, payload.applied_revision && hasPlan ? "good" : "")}
        {summaryMetric("Changed cases", changes.length || payload.change_count || 0)}
        {summaryMetric("Files", changedPaths.length || (payload.schema_changed ? 1 : 0))}
        {summaryMetric("Schema", payload.schema_changed ? "Changed" : "Unchanged")}
      </div>
      <SummaryBlock title="Apply result">
        <strong>{!hasPlan ? "Patch was not generated" : payload.applied_revision ? "Patch applied" : "Patch prepared but not applied"}</strong>
        <p>{!hasPlan ? "The workflow stopped before mutation planning." : payload.applied_revision ? "The mutation was committed to the partition workspace." : "A mutation plan exists, but no committed revision is recorded."}</p>
      </SummaryBlock>
    </>
  );
}

function renderAuditSummary(payload: AnyRecord) {
  const hasError = Boolean(payload.error_message);
  const governance = asRecord(payload.governance_result);
  const runtimeMetadata = asRecord(governance.metadata);
  const runtimeRunId = text(runtimeMetadata.run_id, "");
  const runtimeStatus = text(runtimeMetadata.runtime_status, runtimeRunId ? "Completed" : "Not run");
  return (
    <>
      <div className="knowledge-detail-metrics">
        {summaryMetric("Audit", payload.status, payload.status === "completed" || payload.status === "applied" ? "good" : "review")}
        {summaryMetric("Runtime", runtimeStatus, runtimeStatus === "Completed" ? "good" : "")}
        {summaryMetric("Governance", governance.decision ?? "recorded")}
        {summaryMetric("Review", payload.review_reason ? "Required" : "Clear", payload.review_reason ? "review" : "good")}
      </div>
      <SummaryBlock title={hasError ? "Failure" : "Execution"}>
        <strong>{hasError ? "The drain recorded an error." : runtimeRunId ? "Runtime execution was recorded." : "Only governance and audit were recorded."}</strong>
        <p>{hasError ? text(payload.error_message) : runtimeRunId ? "Detailed runtime, audit, and snapshot data is available in the full record." : "No runtime session was started for this drain."}</p>
      </SummaryBlock>
    </>
  );
}

function renderDecision(payload: AnyRecord) {
  const coverage = asRecord(payload.coverage);
  const proposal = asRecord(payload.proposal);
  const rebuild = asRecord(payload.rebuild);
  const reasons = asArray(payload.reasons);
  return (
    <>
      <div className="knowledge-detail-metrics">
        <Metric label="Decision" value={text(payload.decision)} tone={["accepted", "no_change"].includes(payload.decision) ? "good" : "review"} />
        <Metric label="Risk" value={text(payload.risk_level)} />
        <Metric label="Review" value={payload.requires_review ? "Required" : "Not required"} tone={payload.requires_review ? "review" : "good"} />
        <Metric label="Coverage" value={coverage.coverage_score === undefined ? "--" : `${Math.round(Number(coverage.coverage_score) * 100)}%`} />
      </div>
      <StageStrip stages={asRecord(payload.stages)} />
      <DetailSection title="Governance rationale">
        {reasons.length ? <ul className="knowledge-detail-list">{reasons.map((reason, index) => <li key={`${String(reason)}-${index}`}>{text(reason)}</li>)}</ul> : <EmptyState />}
      </DetailSection>
      <ReasonDetails payload={payload} />
      <DetailSection title="Schema assessment">
        <div className="knowledge-detail-grid">
          <div><span>Existing keys</span><strong>{asArray(coverage.existing_keys).length || "--"}</strong></div>
          <div><span>Touched keys</span><strong>{asArray(coverage.touched_keys).length || "--"}</strong></div>
          <div><span>Rebuild scope</span><strong>{text(rebuild.rebuild_scope)}</strong></div>
          <div><span>Estimated changes</span><strong>{text(rebuild.estimated_change_count)}</strong></div>
        </div>
        {proposal.rationale ? <p className="knowledge-detail-note">{text(proposal.rationale)}</p> : null}
      </DetailSection>
      <DetailSection title="Structured governance record">
        <KnowledgeRecordTree value={payload} />
      </DetailSection>
    </>
  );
}

function renderPatch(payload: AnyRecord) {
  const plan = asRecord(payload.mutation_plan);
  const changes = asArray(plan.case_changes);
  const hasPlan = Object.keys(plan).length > 0;
  const patchStatus = !hasPlan ? "Not generated" : payload.applied_revision ? "Applied" : "Not applied";
  return (
    <>
      <div className="knowledge-detail-metrics">
        <Metric label="Base revision" value={text(payload.base_revision, "pending")} />
        <Metric label="Patch status" value={patchStatus} tone={payload.applied_revision && hasPlan ? "good" : ""} />
        <Metric label="Changed cases" value={String(changes.length || payload.change_count || 0)} />
        <Metric label="Schema" value={payload.schema_changed ? "Changed" : "Unchanged"} />
      </div>
      <DetailSection title="Patch summary">
        <div className="knowledge-detail-grid">
          <div><span>Mutation plan</span><strong>{text(payload.mutation_plan_id || plan.plan_id)}</strong></div>
          <div><span>Patch status</span><strong>{patchStatus}</strong></div>
          <div><span>Partition</span><strong>{text(payload.partition)}</strong></div>
          <div><span>Review</span><strong>{payload.requires_review ? "Required" : "Clear"}</strong></div>
        </div>
        <p className="knowledge-detail-note">{!hasPlan ? "No patch diff exists because mutation planning was not reached." : "This view shows the auditable revision boundary and planned file impact for the selected drain."}</p>
      </DetailSection>
      <DetailSection title="Structured patch context">
        <KnowledgeRecordTree value={payload} />
      </DetailSection>
    </>
  );
}

function renderAudit(payload: AnyRecord) {
  const governance = asRecord(payload.governance_result);
  const runtimeMetadata = asRecord(governance.metadata);
  const runtimeRunId = text(runtimeMetadata.run_id, "");
  const runtimeStatus = text(runtimeMetadata.runtime_status, runtimeRunId ? "completed" : "not run");
  return (
    <>
      <div className="knowledge-detail-metrics">
        <Metric label="Audit status" value={text(payload.status)} tone={payload.status === "completed" || payload.status === "applied" ? "good" : "review"} />
        <Metric label="Runtime" value={runtimeStatus} tone={runtimeStatus === "completed" ? "good" : ""} />
        <Metric label="Decision ID" value={text(payload.decision_id)} />
        <Metric label="Batch ID" value={text(payload.batch_id)} />
        <Metric label="Reviewer" value={text(payload.reviewer, "system")} />
      </div>
      <DetailSection title="Execution record">
        <div className="knowledge-detail-grid">
          <div><span>Created</span><strong>{text(payload.created_at)}</strong></div>
          <div><span>Updated</span><strong>{text(payload.updated_at)}</strong></div>
          <div><span>Statistics fingerprint</span><strong>{text(payload.statistics_fingerprint)}</strong></div>
          <div><span>Supersedes</span><strong>{text(payload.supersedes_decision_id)}</strong></div>
        </div>
        {payload.error_message ? <p className="knowledge-detail-error">{text(payload.error_message)}</p> : null}
        {payload.review_reason ? <p className="knowledge-detail-note">Review reason: {text(payload.review_reason)}</p> : null}
      </DetailSection>
      <DetailSection title="Recorded snapshots">
        <div className="knowledge-detail-snapshot-list">
          <span>Statistics snapshot <strong>{Object.keys(asRecord(payload.statistics_snapshot)).length} fields</strong></span>
          <span>Working set snapshot <strong>{Object.keys(asRecord(payload.working_set_snapshot)).length} fields</strong></span>
          <span>Governance result <strong>{Object.keys(asRecord(payload.governance_result)).length} fields</strong></span>
        </div>
      </DetailSection>
      <DetailSection title="Structured audit record">
        <KnowledgeRecordTree value={payload} />
      </DetailSection>
    </>
  );
}

export function KnowledgeDetailModal({ title, description, payload, onClose, onReviewAction }: KnowledgeDetailModalProps) {
  const [mode, setMode] = useState<"summary" | "details">("summary");
  const record = asRecord(payload);

  useEffect(() => {
    setMode("summary");
  }, [title, payload]);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  const body = mode === "summary"
    ? title === "Input"
      ? <KnowledgeInputStageDetails payload={record} mode="summary" />
      : title === "Preparation"
        ? <KnowledgePreparationStageDetails payload={record} mode="summary" />
      : title === "Proposal"
        ? <KnowledgeProposalStageDetails payload={record} mode="summary" />
      : title === "Runtime"
        ? <KnowledgeRuntimeStageDetails payload={record} mode="summary" />
      : title === "Projection"
        ? <KnowledgeProjectionStageDetails payload={record} mode="summary" />
      : title === "Mutation Plan"
        ? <KnowledgeMutationPlanStageDetails payload={record} mode="summary" />
      : title === "Apply"
        ? <KnowledgeApplyStageDetails payload={record} mode="summary" />
      : title === "Outcome"
        ? <KnowledgeOutcomeStageDetails payload={record} mode="summary" onReviewAction={onReviewAction} />
      : title === "Decision"
      ? renderDecisionSummary(record)
      : title === "Patch Diff"
        ? renderPatchSummary(record)
        : renderAuditSummary(record)
    : title === "Input"
      ? <KnowledgeInputStageDetails payload={record} mode="details" />
      : title === "Preparation"
        ? <KnowledgePreparationStageDetails payload={record} mode="details" />
      : title === "Proposal"
        ? <KnowledgeProposalStageDetails payload={record} mode="details" />
      : title === "Runtime"
        ? <KnowledgeRuntimeStageDetails payload={record} mode="details" />
      : title === "Projection"
        ? <KnowledgeProjectionStageDetails payload={record} mode="details" />
      : title === "Mutation Plan"
        ? <KnowledgeMutationPlanStageDetails payload={record} mode="details" />
      : title === "Apply"
        ? <KnowledgeApplyStageDetails payload={record} mode="details" />
      : title === "Outcome"
        ? <KnowledgeOutcomeStageDetails payload={record} mode="details" onReviewAction={onReviewAction} />
      : title === "Decision"
      ? renderDecision(record)
      : title === "Patch Diff"
        ? renderPatch(record)
      : renderAudit(record);

  return (
    <div className="knowledge-modal-backdrop" role="presentation" onClick={onClose}>
      <section className="knowledge-modal-card" role="dialog" aria-modal="true" aria-labelledby="knowledge-modal-title" onClick={(event) => event.stopPropagation()}>
        <div className="knowledge-modal-head">
          <div>
            <span className="knowledge-section-kicker">Selected Drain · {title}</span>
            <h3 id="knowledge-modal-title">{title}</h3>
            <p>{description}</p>
          </div>
          <div className="knowledge-modal-actions">
            <button type="button" className="knowledge-modal-mode-toggle" onClick={() => setMode(mode === "summary" ? "details" : "summary")}>
              {mode === "summary" ? "View full record" : "Back to summary"}
            </button>
            <button type="button" className="knowledge-modal-close" onClick={onClose}>Close</button>
          </div>
        </div>
        <div className="knowledge-detail-body">{body}</div>
      </section>
    </div>
  );
}
