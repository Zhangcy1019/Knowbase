import type { ReactNode } from "react";

import { KnowledgeRecordTree } from "../KnowledgeRecordTree";
import { effectiveStageStatus } from "../stageStatus";

type KnowledgeApplyStageDetailsProps = {
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

function ApplyAlgorithm() {
  return (
    <div className="knowledge-apply-algorithm">
      <article>
        <strong>1. Validate the plan</strong>
        <p>Confirm the target cases still exist in the same partition and their facets still match the planned before-state.</p>
      </article>
      <article>
        <strong>2. Apply workspace changes</strong>
        <p>Write only the schema and case paths declared by Mutation Plan, then collect the paths actually changed.</p>
      </article>
      <article>
        <strong>3. Commit or roll back</strong>
        <p>Versioning commits the successful mutation. Any failure restores the registered paths and records the rollback.</p>
      </article>
    </div>
  );
}

export function KnowledgeApplyStageDetails({ payload, mode }: KnowledgeApplyStageDetailsProps) {
  const record = asRecord(payload);
  const stage = asRecord(record.stage || record);
  const stageOutput = asRecord(stage.output);
  const execution = asRecord(record.execution);
  const output = Object.keys(stageOutput).length ? stageOutput : stage;
  const plannedPaths = asArray(output.planned_paths).length
    ? asArray(output.planned_paths)
    : asArray(execution.planned_paths);
  const changedPaths = asArray(output.changed_paths).length
    ? asArray(output.changed_paths)
    : asArray(output.updated_paths).length
      ? asArray(output.updated_paths)
      : asArray(execution.changed_paths);
  const updatedCases = asArray(output.updated_case_ids).length
    ? asArray(output.updated_case_ids)
    : asArray(execution.updated_case_ids);
  const revision = output.applied_revision || output.revision || execution.applied_revision;
  const rolledBack = output.rolled_back === true || execution.rolled_back === true;
  const hasError = Boolean(stage.error || output.error || execution.error);
  const status = effectiveStageStatus("Apply", record, "not run");
  const statusVariant = status === "completed" ? "good" : status === "passed" ? "" : "review";

  return (
    <>
      <div className="knowledge-detail-metrics">
        <Metric label="Apply status" value={status} variant={statusVariant} />
        <Metric label="Changed paths" value={String(changedPaths.length)} variant={changedPaths.length ? "review" : "good"} />
        <Metric label="Updated cases" value={String(updatedCases.length)} />
        <Metric label="Revision" value={text(revision, "Not committed")} />
      </div>

      <div className="knowledge-summary-grid">
        <section className={`knowledge-summary-block${hasError || rolledBack ? " is-warning" : ""}`}>
          <span>Apply result</span>
          <strong>
            {status === "not run"
              ? "Apply was not reached"
              : hasError
                ? "Apply failed"
                : rolledBack
                  ? "Changes were rolled back"
                  : changedPaths.length
                    ? "Workspace changes were committed"
                    : "Plan was checked; no workspace change was needed"}
          </strong>
          <p>{text(stage.error || output.error || execution.error, rolledBack ? "The mutation was reverted after an apply failure." : "Apply records the actual write and version-control result.")}</p>
        </section>
        <section className="knowledge-summary-block">
          <span>Execution boundary</span>
          <strong>{revision ? "Committed revision recorded" : "No commit recorded"}</strong>
          <p>Only this stage can modify the partition workspace. The plan remains unchanged and is retained for audit.</p>
        </section>
      </div>

      <Section title="How Apply works">
        <ApplyAlgorithm />
      </Section>

      <Section title="Workspace impact">
        <div className="knowledge-apply-scope">
          <div><span>Planned paths</span><strong>{String(plannedPaths.length)}</strong></div>
          <div><span>Changed paths</span><strong>{String(changedPaths.length)}</strong></div>
          <div><span>Updated cases</span><strong>{String(updatedCases.length)}</strong></div>
          <div><span>Rollback</span><strong>{rolledBack ? "Yes" : "No"}</strong></div>
        </div>
        {plannedPaths.length ? (
          <div className="knowledge-apply-path-group">
            <span>Planned paths</span>
            <p>{plannedPaths.map((path) => text(path)).join(" · ")}</p>
          </div>
        ) : null}
        {changedPaths.length ? (
          <div className="knowledge-apply-path-group is-changed">
            <span>Actually changed</span>
            <p>{changedPaths.map((path) => text(path)).join(" · ")}</p>
          </div>
        ) : null}
      </Section>

      {updatedCases.length ? (
        <Section title="Updated cases">
          <div className="knowledge-apply-case-list">
            {updatedCases.slice(0, 20).map((caseId, index) => <span key={`${text(caseId)}-${index}`}>{text(caseId)}</span>)}
          </div>
          {updatedCases.length > 20 ? <p className="knowledge-detail-note">Showing the first 20 updated cases.</p> : null}
        </Section>
      ) : null}

      {mode === "details" ? (
        <Section title="Structured Apply record">
          <KnowledgeRecordTree value={payload} />
        </Section>
      ) : (
        <p className="knowledge-detail-note">Switch to full record to inspect commit paths, rollback state, and the complete execution result.</p>
      )}
    </>
  );
}
