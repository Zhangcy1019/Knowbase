import type { ReactNode } from "react";

type KnowledgeDetailModalProps = {
  title: string;
  description: string;
  payload: unknown;
  onClose: () => void;
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

function prettyValues(value: unknown) {
  const record = asRecord(value);
  return Object.entries(record)
    .map(([key, values]) => `${key}: ${Array.isArray(values) ? values.join(", ") : text(values)}`)
    .join(" · ");
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

function fieldLabel(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function DetailValue({ value }: { value: unknown }) {
  if (value === null || value === undefined || value === "") {
    return <span className="knowledge-detail-value-empty">--</span>;
  }
  if (typeof value !== "object") {
    return <span className="knowledge-detail-value-text">{String(value)}</span>;
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="knowledge-detail-value-empty">Empty</span>;
    return (
      <div className="knowledge-detail-array">
        {value.map((item, index) => (
          <div className="knowledge-detail-array-item" key={index}>
            <DetailValue value={item} />
          </div>
        ))}
      </div>
    );
  }
  const entries = Object.entries(value as AnyRecord);
  if (entries.length === 0) return <span className="knowledge-detail-value-empty">Empty object</span>;
  return (
    <div className="knowledge-detail-object">
      {entries.map(([key, item]) => (
        <div className="knowledge-detail-field" key={key}>
          <span className="knowledge-detail-field-label">{fieldLabel(key)}</span>
          <DetailValue value={item} />
        </div>
      ))}
    </div>
  );
}

function EmptyState({ children = "No data recorded." }: { children?: ReactNode }) {
  return <div className="knowledge-detail-empty">{children}</div>;
}

function renderDecision(payload: AnyRecord) {
  const coverage = asRecord(payload.coverage);
  const proposal = asRecord(payload.proposal);
  const rebuild = asRecord(payload.rebuild);
  const reasons = asArray(payload.reasons);
  return (
    <>
      <div className="knowledge-detail-metrics">
        <Metric label="Decision" value={text(payload.decision)} tone={payload.decision === "accepted" ? "good" : "review"} />
        <Metric label="Risk" value={text(payload.risk_level)} />
        <Metric label="Review" value={payload.requires_review ? "Required" : "Not required"} tone={payload.requires_review ? "review" : "good"} />
        <Metric label="Coverage" value={coverage.coverage_score === undefined ? "--" : `${Math.round(Number(coverage.coverage_score) * 100)}%`} />
      </div>
      <DetailSection title="Governance rationale">
        {reasons.length ? <ul className="knowledge-detail-list">{reasons.map((reason, index) => <li key={`${String(reason)}-${index}`}>{text(reason)}</li>)}</ul> : <EmptyState />}
      </DetailSection>
      <DetailSection title="Schema assessment">
        <div className="knowledge-detail-grid">
          <div><span>Existing keys</span><strong>{asArray(coverage.existing_keys).length || "--"}</strong></div>
          <div><span>Touched keys</span><strong>{asArray(coverage.touched_keys).length || "--"}</strong></div>
          <div><span>Rebuild scope</span><strong>{text(rebuild.rebuild_scope)}</strong></div>
          <div><span>Estimated changes</span><strong>{text(rebuild.estimated_change_count)}</strong></div>
        </div>
        {proposal.rationale ? <p className="knowledge-detail-note">{text(proposal.rationale)}</p> : null}
      </DetailSection>
      <DetailSection title="Complete governance record">
        <DetailValue value={payload} />
      </DetailSection>
    </>
  );
}

function renderMutationPlan(payload: AnyRecord) {
  const changes = asArray(payload.case_changes).map(asRecord);
  return (
    <>
      <div className="knowledge-detail-metrics">
        <Metric label="Plan ID" value={text(payload.plan_id)} />
        <Metric label="Partition" value={text(payload.partition)} />
        <Metric label="Risk" value={text(payload.risk_level)} />
        <Metric label="Case changes" value={String(changes.length)} />
      </div>
      {payload.summary ? <p className="knowledge-detail-note">{text(payload.summary)}</p> : null}
      <DetailSection title="Planned case changes">
        {changes.length ? (
          <div className="knowledge-change-list">
            {changes.map((change, index) => (
              <article className="knowledge-change-row" key={`${text(change.case_id, "change")}-${index}`}>
                <div className="knowledge-change-head"><strong>{text(change.case_id)}</strong><span>Facet update</span></div>
                <div className="knowledge-change-values">
                  <div><span>Before</span><p>{prettyValues(change.before_facets) || "No facets"}</p></div>
                  <div><span>After</span><p>{prettyValues(change.after_facets) || "No facets"}</p></div>
                </div>
              </article>
            ))}
          </div>
        ) : <EmptyState>No case changes in this plan.</EmptyState>}
      </DetailSection>
      <DetailSection title="Complete mutation plan">
        <DetailValue value={payload} />
      </DetailSection>
    </>
  );
}

function renderPatch(payload: AnyRecord) {
  const plan = asRecord(payload.mutation_plan);
  const changes = asArray(plan.case_changes);
  return (
    <>
      <div className="knowledge-detail-metrics">
        <Metric label="Base revision" value={text(payload.base_revision, "pending")} />
        <Metric label="Applied revision" value={text(payload.applied_revision, "not applied")} tone={payload.applied_revision ? "good" : ""} />
        <Metric label="Changed cases" value={String(changes.length || payload.change_count || 0)} />
        <Metric label="Schema" value={payload.schema_changed ? "Changed" : "Unchanged"} />
      </div>
      <DetailSection title="Patch summary">
        <div className="knowledge-detail-grid">
          <div><span>Mutation plan</span><strong>{text(payload.mutation_plan_id || plan.plan_id)}</strong></div>
          <div><span>Status</span><strong>{text(payload.status)}</strong></div>
          <div><span>Partition</span><strong>{text(payload.partition)}</strong></div>
          <div><span>Review</span><strong>{payload.requires_review ? "Required" : "Clear"}</strong></div>
        </div>
        <p className="knowledge-detail-note">This view shows the auditable revision boundary and planned file impact for the selected drain.</p>
      </DetailSection>
      <DetailSection title="Complete patch context">
        <DetailValue value={payload} />
      </DetailSection>
    </>
  );
}

function renderAudit(payload: AnyRecord) {
  return (
    <>
      <div className="knowledge-detail-metrics">
        <Metric label="Status" value={text(payload.status)} tone={payload.status === "completed" || payload.status === "applied" ? "good" : "review"} />
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
      <DetailSection title="Complete audit record">
        <DetailValue value={payload} />
      </DetailSection>
    </>
  );
}

export function KnowledgeDetailModal({ title, description, payload, onClose }: KnowledgeDetailModalProps) {
  const record = asRecord(payload);
  const body = title === "Decision"
    ? renderDecision(record)
    : title === "Mutation Plan"
      ? renderMutationPlan(record)
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
          <button type="button" className="knowledge-modal-close" onClick={onClose}>Close</button>
        </div>
        <div className="knowledge-detail-body">{body}</div>
      </section>
    </div>
  );
}
