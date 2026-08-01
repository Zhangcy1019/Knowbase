import type { ReactNode } from "react";

import { KnowledgeRecordTree } from "../KnowledgeRecordTree";
import { effectiveStageStatus } from "../stageStatus";

type KnowledgeMutationPlanStageDetailsProps = {
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

function PlanAlgorithm() {
  return (
    <div className="knowledge-mutation-plan-algorithm">
      <article>
        <strong>1. Freeze accepted inputs</strong>
        <p>Combine the accepted schema decision and projection changes from this drain. No new analysis is performed here.</p>
      </article>
      <article>
        <strong>2. Build an auditable plan</strong>
        <p>Record schema changes, case before/after facets, affected IDs, risk, reasons, and the workspace paths that may change.</p>
      </article>
      <article>
        <strong>3. Keep execution separate</strong>
        <p>Mutation Plan describes intended writes only. Apply validates and performs them; versioning commits or rolls them back.</p>
      </article>
    </div>
  );
}

export function KnowledgeMutationPlanStageDetails({ payload, mode }: KnowledgeMutationPlanStageDetailsProps) {
  const record = asRecord(payload);
  const stage = asRecord(record.stage || record);
  const stageOutput = asRecord(stage.output);
  const plan = Object.keys(stageOutput).length ? stageOutput : stage;
  const execution = asRecord(record.execution);
  const changes = asArray(plan.case_changes);
  const affectedCaseIds = asArray(plan.affected_case_ids);
  const plannedPaths = asArray(plan.planned_paths).length
    ? asArray(plan.planned_paths)
    : asArray(execution.planned_paths);
  const hasSchemaChange = plan.accepted_schema !== null && plan.accepted_schema !== undefined;
  const hasPlan = Boolean(
    plan.plan_id
      || plan.batch_id
      || plan.created_at
      || Array.isArray(plan.case_changes)
      || Object.prototype.hasOwnProperty.call(plan, "accepted_schema"),
  );
  const status = effectiveStageStatus("Mutation Plan", record, hasPlan ? "no_action" : "not run");
  const statusVariant = status === "completed" ? "good" : status === "no_action" || status === "passed" ? "" : "review";

  return (
    <>
      <div className="knowledge-detail-metrics">
        <Metric label="Plan status" value={status} variant={statusVariant} />
        <Metric label="Case changes" value={String(changes.length)} variant={changes.length ? "review" : "good"} />
        <Metric label="Schema change" value={hasSchemaChange ? "Yes" : "No"} variant={hasSchemaChange ? "review" : "good"} />
        <Metric label="Planned paths" value={String(plannedPaths.length)} />
      </div>

      <div className="knowledge-summary-grid">
        <section className={`knowledge-summary-block${status === "blocked" || status === "failed" ? " is-warning" : ""}`}>
          <span>Plan result</span>
          <strong>
            {!hasPlan || status === "not run"
              ? "Mutation planning was not reached"
              : status === "no_action"
                ? "No write action is required"
                : `${changes.length + (hasSchemaChange ? 1 : 0)} mutation target(s) recorded`}
          </strong>
          <p>{text(plan.summary, "The plan packages accepted governance output into an auditable mutation boundary.")}</p>
        </section>
        <section className="knowledge-summary-block">
          <span>Write boundary</span>
          <strong>Plan only · workspace unchanged</strong>
          <p>Creating this record does not modify case files or the partition schema. Apply is the first stage allowed to write.</p>
        </section>
      </div>

      <Section title="How Mutation Plan works">
        <PlanAlgorithm />
      </Section>

      {hasPlan ? (
        <Section title="Plan scope">
          <div className="knowledge-mutation-plan-scope">
            <div><span>Plan ID</span><strong>{text(plan.plan_id)}</strong></div>
            <div><span>Partition</span><strong>{text(plan.partition)}</strong></div>
            <div><span>Risk</span><strong>{text(plan.risk_level)}</strong></div>
            <div><span>Affected cases</span><strong>{String(affectedCaseIds.length || changes.length)}</strong></div>
          </div>
          {plannedPaths.length ? (
            <div className="knowledge-mutation-plan-paths">
              <span>Potential workspace paths</span>
              <p>{plannedPaths.map((path) => text(path)).join(" · ")}</p>
            </div>
          ) : null}
        </Section>
      ) : null}

      {changes.length ? (
        <Section title="Planned case changes">
          <div className="knowledge-mutation-change-list">
            {changes.slice(0, 12).map((change, index) => {
              const item = asRecord(change);
              return (
                <article key={`${text(item.case_id, "case")}-${index}`}>
                  <div className="knowledge-mutation-change-head">
                    <strong>{text(item.case_id, "case")}</strong>
                    <span>{asArray(item.changed_keys).length || "facet"} change(s)</span>
                  </div>
                  <div className="knowledge-mutation-change-values">
                    <div><span>Before</span><KnowledgeRecordTree value={item.before_facets} /></div>
                    <div><span>After</span><KnowledgeRecordTree value={item.after_facets} /></div>
                  </div>
                </article>
              );
            })}
          </div>
          {changes.length > 12 ? <p className="knowledge-detail-note">Showing the first 12 changes. The full plan contains {changes.length} case changes.</p> : null}
        </Section>
      ) : null}

      {mode === "details" ? (
        <Section title="Structured mutation plan record">
          <KnowledgeRecordTree value={payload} />
        </Section>
      ) : (
        <p className="knowledge-detail-note">Switch to full record to inspect accepted schema, reasons, and every before/after facet value.</p>
      )}
    </>
  );
}
