import type { ReactNode } from "react";
import { useState } from "react";

import { KnowledgeRecordTree } from "../KnowledgeRecordTree";

type KnowledgeOutcomeStageDetailsProps = {
  payload: unknown;
  mode: "summary" | "details";
  onReviewAction?: (action: "approve" | "discard" | "retry") => Promise<void>;
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

function outcomeTone(value: string) {
  if (["accepted", "completed", "applied"].includes(value)) return "good";
  if (["requires_review", "failed", "blocked", "discarded"].includes(value)) return "review";
  return "";
}

function Metric({ label, value, variant = "" }: { label: string; value: string; variant?: string }) {
  return <div className={`knowledge-detail-metric${variant ? ` is-${variant}` : ""}`}><span>{label}</span><strong>{value}</strong></div>;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return <section className="knowledge-detail-section"><h4>{title}</h4>{children}</section>;
}

function OutcomeAlgorithm() {
  return (
    <div className="knowledge-outcome-algorithm">
      <article><strong>1. Collect stage results</strong><p>Summarize the recorded preparation, proposal, runtime, projection, plan, and apply results.</p></article>
      <article><strong>2. Preserve the final reason</strong><p>Keep reasons and root-cause details instead of reducing every stop to a generic completed status.</p></article>
      <article><strong>3. Keep the lifecycle visible</strong><p>Record every transition, including review, approval, retry, failure, or successful completion.</p></article>
    </div>
  );
}

export function KnowledgeOutcomeStageDetails({ payload, mode, onReviewAction }: KnowledgeOutcomeStageDetailsProps) {
  const [pendingAction, setPendingAction] = useState("");
  const [actionError, setActionError] = useState("");
  const record = asRecord(payload);
  const outcome = asRecord(record.outcome);
  const status = text(outcome.outcome || record.status, "not recorded");
  const reasons = asArray(outcome.reasons || record.reasons);
  const reasonDetails = asArray(outcome.reason_details || record.reason_details);
  const history = asArray(record.status_history);
  const reviewer = text(record.reviewer, "System");
  const reviewReason = text(record.review_reason, "No manual review");
  const requiresReview = status === "requires_review" || Boolean(record.review_reason);
  const decisionId = text(record.decision_id, "");

  const runReviewAction = async (action: "approve" | "discard" | "retry") => {
    if (!onReviewAction) return;
    const labels = { approve: "approve", discard: "discard", retry: "request a retry" };
    if (!window.confirm(`Confirm: ${labels[action]} this Knowledge decision?`)) return;
    setPendingAction(action);
    setActionError("");
    try {
      await onReviewAction(action);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Review action failed.");
    } finally {
      setPendingAction("");
    }
  };

  return (
    <>
      <div className="knowledge-detail-metrics">
        <Metric label="Final outcome" value={status} variant={outcomeTone(status)} />
        <Metric label="Reasons" value={String(reasons.length + reasonDetails.length)} variant={reasons.length || reasonDetails.length ? "review" : "good"} />
        <Metric label="Transitions" value={String(history.length)} />
        <Metric label="Review" value={requiresReview ? "Required" : "Not required"} variant={requiresReview ? "review" : "good"} />
      </div>

      <div className="knowledge-summary-grid">
        <section className={`knowledge-summary-block${requiresReview || status === "failed" ? " is-warning" : ""}`}>
          <span>Final conclusion</span>
          <strong>{status === "no_change" ? "No actionable change" : status === "not recorded" ? "Outcome not recorded" : status}</strong>
          <p>{reasons.length ? text(reasons[0]) : "The outcome was recorded without a top-level reason."}</p>
        </section>
        <section className="knowledge-summary-block">
          <span>Review state</span>
          <strong>{requiresReview ? "Waiting for human decision" : `Resolved by ${reviewer}`}</strong>
          <p>{requiresReview ? reviewReason : "No manual review is currently required for this drain."}</p>
        </section>
      </div>

      <Section title="How Outcome works"><OutcomeAlgorithm /></Section>

      {reasons.length ? <Section title="Conclusion reasons"><ul className="knowledge-detail-list">{reasons.map((reason, index) => <li key={index}>{text(reason)}</li>)}</ul></Section> : null}
      {reasonDetails.length ? <Section title="Root-cause details"><KnowledgeRecordTree value={reasonDetails} /></Section> : null}

      {requiresReview && decisionId && onReviewAction ? (
        <Section title="Manual review actions">
          <div className="knowledge-review-actions">
            <button type="button" onClick={() => runReviewAction("approve")} disabled={Boolean(pendingAction)}>{pendingAction === "approve" ? "Approving..." : "Approve & unlock"}</button>
            <button type="button" onClick={() => runReviewAction("retry")} disabled={Boolean(pendingAction)}>{pendingAction === "retry" ? "Requesting..." : "Release & retry"}</button>
            <button type="button" className="is-danger" onClick={() => runReviewAction("discard")} disabled={Boolean(pendingAction)}>{pendingAction === "discard" ? "Discarding..." : "Discard decision"}</button>
          </div>
          <p className="knowledge-detail-note">Approve records approval and unlocks the partition. Retry releases the lock so a new drain can be triggered. Discard closes this proposal.</p>
          {actionError ? <p className="knowledge-detail-error">{actionError}</p> : null}
        </Section>
      ) : null}

      {mode === "details" ? (
        <>
          <Section title="Status history">{history.length ? <KnowledgeRecordTree value={history} /> : <p className="knowledge-detail-note">No status transitions were recorded.</p>}</Section>
          <Section title="Structured outcome record"><KnowledgeRecordTree value={payload} /></Section>
        </>
      ) : <p className="knowledge-detail-note">Switch to full record to inspect every transition, reviewer decision, and root-cause detail.</p>}
    </>
  );
}
