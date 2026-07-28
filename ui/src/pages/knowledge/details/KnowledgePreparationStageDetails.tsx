import type { ReactNode } from "react";

import { KnowledgeRecordTree } from "../KnowledgeRecordTree";
import { effectiveStageStatus } from "../stageStatus";

type KnowledgePreparationStageDetailsProps = {
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

function coverageValue(value: unknown) {
  const coverage = asRecord(value).coverage_score ?? value;
  if (coverage === undefined || coverage === null || coverage === "") return "--";
  const number = Number(coverage);
  if (!Number.isFinite(number)) return text(coverage);
  return `${Math.round(number <= 1 ? number * 100 : number)}%`;
}

function statusTone(status: string) {
  if (["completed", "consistent", "ready"].includes(status)) return "good";
  if (["blocked", "stale", "inconsistent"].includes(status)) return "review";
  if (status === "failed") return "failed";
  return "";
}

function Metric({ label, value, tone = "" }: { label: string; value: string; tone?: string }) {
  return (
    <div className={`knowledge-detail-metric${tone ? ` is-${tone}` : ""}`}>
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

export function KnowledgePreparationStageDetails({ payload, mode }: KnowledgePreparationStageDetailsProps) {
  const record = asRecord(payload);
  const stage = asRecord(record.stage || record);
  const output = asRecord(stage.output);
  const coverage = asRecord(output.coverage);
  const mismatches = asArray(output.consistency_mismatches);
  const rebuild = asRecord(output.rebuild);
  const status = effectiveStageStatus("Preparation", record);
  const consistency = text(output.consistency_status, "not checked");
  const blocked = status === "blocked" || consistency === "inconsistent" || consistency === "stale";

  return (
    <>
      <div className="knowledge-detail-metrics">
        <Metric label="Stage status" value={status} tone={statusTone(status)} />
        <Metric label="Evidence consistency" value={consistency} tone={statusTone(consistency)} />
        <Metric label="Coverage" value={coverageValue(coverage)} />
        <Metric label="Mismatches" value={String(mismatches.length)} tone={mismatches.length ? "review" : "good"} />
      </div>

      <div className="knowledge-summary-grid">
        <section className={`knowledge-summary-block${blocked ? " is-warning" : ""}`}>
          <span>Evidence health</span>
          <strong>{blocked ? "Evidence cannot be used safely" : "Evidence is ready for proposal analysis"}</strong>
          <p>{blocked ? "The statistics snapshot and materialized indexes need attention before schema proposal." : "Preparation found no blocking evidence mismatch."}</p>
        </section>
        <section className="knowledge-summary-block">
          <span>Rebuild assessment</span>
          <strong>{text(rebuild.rebuild_scope, "No rebuild requested")}</strong>
          <p>{text(rebuild.estimated_change_count, "0")} estimated case change(s) are associated with this preparation result.</p>
        </section>
      </div>

      {blocked ? (
        <Section title="Why proposal is blocked">
          <div className="knowledge-reason-list">
            {mismatches.length ? mismatches.slice(0, 8).map((mismatch, index) => (
              <div className="knowledge-reason-item" key={index}>
                <div className="knowledge-reason-item-head">
                  <strong>{text(asRecord(mismatch).kind, "Evidence mismatch")}</strong>
                  <span>{text(asRecord(mismatch).source, "preparation")}</span>
                </div>
                <p>{text(asRecord(mismatch).message || asRecord(mismatch).key, "Statistics and index data do not describe the same state.")}</p>
              </div>
            )) : <p className="knowledge-detail-note">Preparation was blocked without a structured mismatch detail.</p>}
          </div>
        </Section>
      ) : null}

      <Section title="Preparation measurements">
        <div className="knowledge-detail-grid">
          <div><span>Existing keys</span><strong>{String(asArray(coverage.existing_keys).length)}</strong></div>
          <div><span>Touched keys</span><strong>{String(asArray(coverage.touched_keys).length)}</strong></div>
          <div><span>Rebuild scope</span><strong>{text(rebuild.rebuild_scope)}</strong></div>
          <div><span>Estimated changes</span><strong>{text(rebuild.estimated_change_count, "0")}</strong></div>
        </div>
      </Section>

      {mode === "details" ? (
        <Section title="Structured preparation record">
          <KnowledgeRecordTree value={payload} />
        </Section>
      ) : (
        <p className="knowledge-detail-note">Switch to full record to inspect all consistency mismatches and preparation evidence.</p>
      )}
    </>
  );
}
