import type { ReactNode } from "react";

import { KnowledgeRecordTree } from "../KnowledgeRecordTree";

type KnowledgeInputStageDetailsProps = {
  payload: unknown;
  mode: "summary" | "details";
};

type AnyRecord = Record<string, unknown>;

function asRecord(value: unknown): AnyRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? value as AnyRecord : {};
}

function text(value: unknown, fallback = "--") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function countFields(value: unknown) {
  return Object.keys(asRecord(value)).length;
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="knowledge-detail-metric">
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

export function KnowledgeInputStageDetails({ payload, mode }: KnowledgeInputStageDetailsProps) {
  const input = asRecord(payload);
  const statistics = asRecord(input.statistics_snapshot);
  const workingSet = asRecord(input.working_set);
  const isDetailed = mode === "details";

  return (
    <>
      <div className="knowledge-detail-metrics">
        <Metric label="Base revision" value={text(input.base_revision, "Not available")} />
        <Metric label="Statistics" value={input.statistics_fingerprint ? "Fingerprint recorded" : "Not recorded"} />
        <Metric label="Statistics fields" value={String(countFields(statistics))} />
        <Metric label="Working set fields" value={String(countFields(workingSet))} />
      </div>

      <div className="knowledge-summary-grid">
        <section className="knowledge-summary-block">
          <span>Evidence boundary</span>
          <strong>{input.base_revision ? "Pinned to a workspace revision" : "Revision was not captured"}</strong>
          <p>All governance stages should reason from this revision rather than from later workspace changes.</p>
        </section>
        <section className="knowledge-summary-block">
          <span>Frozen evidence</span>
          <strong>{input.statistics_fingerprint ? "Statistics snapshot captured" : "Statistics snapshot unavailable"}</strong>
          <p>The snapshot and working set are the inputs used to reproduce this drain.</p>
        </section>
      </div>

      <Section title="Captured input">
        <div className="knowledge-detail-grid">
          <div><span>Base revision</span><strong>{text(input.base_revision)}</strong></div>
          <div><span>Statistics fingerprint</span><strong>{text(input.statistics_fingerprint)}</strong></div>
          <div><span>Statistics snapshot</span><strong>{countFields(statistics)} fields</strong></div>
          <div><span>Working set</span><strong>{countFields(workingSet)} fields</strong></div>
        </div>
      </Section>

      {isDetailed ? (
        <>
          <Section title="Statistics snapshot">
            <KnowledgeRecordTree value={statistics} />
          </Section>
          <Section title="Working set snapshot">
            <KnowledgeRecordTree value={workingSet} />
          </Section>
          <Section title="Structured input record">
            <KnowledgeRecordTree value={input} />
          </Section>
        </>
      ) : (
        <p className="knowledge-detail-note">Switch to full record to inspect the captured statistics and working-set fields.</p>
      )}
    </>
  );
}
