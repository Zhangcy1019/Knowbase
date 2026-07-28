import type { ReactNode } from "react";

import { KnowledgeRecordTree } from "../KnowledgeRecordTree";
import { effectiveStageStatus } from "../stageStatus";

type KnowledgeProjectionStageDetailsProps = {
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

function ProjectionAlgorithm() {
  return (
    <div className="knowledge-projection-algorithm">
      <article>
        <strong>1. Re-resolve facets</strong>
        <p>Use each case semantic profile and the accepted schema to calculate the projected facet representation.</p>
      </article>
      <article>
        <strong>2. Compare before / after</strong>
        <p>Only keys whose facet values differ are emitted as a CaseProjectionChange.</p>
      </article>
      <article>
        <strong>3. Keep writes separate</strong>
        <p>Projection only creates an impact plan. Mutation Plan and Apply are responsible for actual file changes.</p>
      </article>
    </div>
  );
}

export function KnowledgeProjectionStageDetails({ payload, mode }: KnowledgeProjectionStageDetailsProps) {
  const record = asRecord(payload);
  const stage = asRecord(record.stage || record);
  const output = asRecord(stage.output || stage);
  const changes = asArray(output.changes);
  const unchanged = asArray(output.unchanged_case_ids);
  const skipped = asArray(output.skipped_case_ids);
  const targets = asArray(output.target_case_ids);
  const status = effectiveStageStatus("Projection", record);

  return (
    <>
      <div className="knowledge-detail-metrics">
        <Metric label="Projection status" value={status} variant={status === "completed" ? "good" : status === "not run" ? "" : "review"} />
        <Metric label="Target cases" value={String(targets.length)} />
        <Metric label="Facet changes" value={String(changes.length)} variant={changes.length ? "review" : "good"} />
        <Metric label="Unchanged / skipped" value={`${unchanged.length} / ${skipped.length}`} />
      </div>

      <div className="knowledge-summary-grid">
        <section className="knowledge-summary-block">
          <span>Impact result</span>
          <strong>{changes.length ? `${changes.length} case(s) would change` : "No case facet changes"}</strong>
          <p>{unchanged.length} case(s) already match the accepted schema; {skipped.length} case(s) could not be projected.</p>
        </section>
        <section className="knowledge-summary-block">
          <span>Write boundary</span>
          <strong>Read-only projection</strong>
          <p>This stage compares representations only. It does not modify case files, indexes, or the Git workspace.</p>
        </section>
      </div>

      <Section title="How projection works">
        <ProjectionAlgorithm />
      </Section>

      {changes.length ? (
        <Section title="Affected cases">
          <div className="knowledge-projection-change-list">
            {changes.slice(0, 12).map((change, index) => {
              const item = asRecord(change);
              return (
                <article key={index}>
                  <div><strong>{text(item.case_id, "case")}</strong><span>{asArray(item.changed_keys).length} changed key(s)</span></div>
                  <p>{asArray(item.changed_keys).map((key) => text(key)).join(", ") || "Facet representation changed"}</p>
                </article>
              );
            })}
          </div>
          {changes.length > 12 ? <p className="knowledge-detail-note">Showing the first 12 changes. Full projection data is available in the detailed record.</p> : null}
        </Section>
      ) : null}

      {mode === "details" ? (
        <Section title="Structured projection record">
          <KnowledgeRecordTree value={payload} />
        </Section>
      ) : (
        <p className="knowledge-detail-note">Switch to full record to inspect before/after facets and skipped case IDs.</p>
      )}
    </>
  );
}
