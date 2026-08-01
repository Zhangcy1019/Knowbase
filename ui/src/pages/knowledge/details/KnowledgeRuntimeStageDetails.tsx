import type { ReactNode } from "react";

import { KnowledgeRecordTree } from "../KnowledgeRecordTree";

type KnowledgeRuntimeStageDetailsProps = {
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
  if (["completed", "accepted", "no_change"].includes(status)) return "good";
  if (["requires_review", "failed", "stopped"].includes(status)) return "review";
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

function RuntimeContract() {
  return (
    <div className="knowledge-runtime-contract">
      <article>
        <strong>Read-only analysis</strong>
        <p>Runtime may inspect evidence and call allowlisted read capabilities, but cannot edit files or apply mutations.</p>
      </article>
      <article>
        <strong>Governance decision</strong>
        <p>It returns no_change, accepted, or requires_review with reasons and, when accepted, a complete replacement schema.</p>
      </article>
      <article>
        <strong>Validation gate</strong>
        <p>An accepted schema must pass governance.validate_candidate before the runtime can stop successfully.</p>
      </article>
    </div>
  );
}

export function KnowledgeRuntimeStageDetails({ payload, mode }: KnowledgeRuntimeStageDetailsProps) {
  const record = asRecord(payload);
  const stage = asRecord(record.stage || record);
  const output = asRecord(stage.output);
  const metadata = asRecord(output.metadata);
  const details = asArray(output.details);
  const validation = asRecord(metadata.validation);
  const governanceDecision = asRecord(metadata.governance_decision);
  const status = text(stage.status, "not run");
  const runtimeStatus = text(metadata.runtime_status, status === "not run" ? "not run" : "recorded");
  const runtimeRunId = text(record.runtime_run_id || metadata.run_id, "");
  const outcome = text(governanceDecision.outcome, "not returned");
  const failed = status === "failed" || runtimeStatus === "failed";

  return (
    <>
      <div className="knowledge-detail-metrics">
        <Metric label="Runtime status" value={runtimeStatus} variant={failed ? "review" : tone(runtimeStatus)} />
        <Metric label="Governance outcome" value={outcome} variant={tone(outcome)} />
        <Metric label="Validation" value={validation.passed === true ? "Passed" : validation.passed === false ? "Failed" : "Not recorded"} variant={validation.passed === true ? "good" : validation.passed === false ? "review" : ""} />
        <Metric label="Runtime run" value={runtimeRunId || "Not started"} />
      </div>

      <div className="knowledge-summary-grid">
        <section className={`knowledge-summary-block${failed ? " is-warning" : ""}`}>
          <span>What runtime did</span>
          <strong>{status === "not run" ? "Runtime was not started" : failed ? "Runtime did not complete" : "Read-only governance analysis"}</strong>
          <p>{failed ? text(stage.error, "The runtime ended before producing a usable decision.") : "Runtime reviewed the deterministic proposal and returned a governance recommendation without changing the workspace."}</p>
        </section>
        <section className="knowledge-summary-block">
          <span>Recorded evidence</span>
          <strong>{details.length} runtime detail record(s)</strong>
          <p>{validation.passed === true ? "The candidate validation result passed before the runtime completed." : "Validation is recorded as a skill result inside the runtime run; it does not have a separate run ID."}</p>
        </section>
      </div>

      <Section title="Runtime contract">
        <RuntimeContract />
        {runtimeRunId ? (
          <a className="knowledge-runtime-link" href={`/runs?run_id=${encodeURIComponent(runtimeRunId)}`}>
            Open runtime trace <span aria-hidden="true">→</span>
          </a>
        ) : null}
      </Section>

      {governanceDecision.reasons ? (
        <Section title="Runtime decision reasons">
          <ul className="knowledge-detail-list">
            {asArray(governanceDecision.reasons).map((reason, index) => <li key={index}>{text(reason)}</li>)}
          </ul>
        </Section>
      ) : null}

      {mode === "details" ? (
        <>
          <Section title="Runtime details">
            {details.length ? <KnowledgeRecordTree value={details} /> : <p className="knowledge-detail-note">No runtime detail records were captured.</p>}
          </Section>
          <Section title="Structured runtime record">
            <KnowledgeRecordTree value={payload} />
          </Section>
        </>
      ) : (
        <p className="knowledge-detail-note">Switch to full record to inspect runtime metadata, decision output, and validation evidence.</p>
      )}
    </>
  );
}
