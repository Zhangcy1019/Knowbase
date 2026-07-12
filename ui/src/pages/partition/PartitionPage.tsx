import { useMemo, useState } from "react";
import "./partition.css";

const partitionSummary = [
  { label: "Cases", value: "516", note: "indexed" },
  { label: "Facet keys", value: "7", note: "stable" },
  { label: "Semantic keys", value: "28", note: "observed" },
  { label: "Facet values", value: "143", note: "active" },
];

type SchemaEntry = {
  key: string;
  description: string;
  count: string;
  values: Array<{ value: string; count: string }>;
  status?: "stable" | "review" | "elevated";
  source: "facet" | "semantic";
};

const facetSchemaRows: SchemaEntry[] = [
  {
    key: "team",
    description: "Owning business team for intake and review.",
    count: "401",
    status: "stable",
    source: "facet",
    values: [
      { value: "claims_ops", count: "88" },
      { value: "policy_admin", count: "74" },
      { value: "audit_desk", count: "51" },
      { value: "appeal_unit", count: "43" },
      { value: "finance_review", count: "29" },
    ],
  },
  {
    key: "priority",
    description: "Operational priority used for queue shaping.",
    count: "336",
    status: "stable",
    source: "facet",
    values: [
      { value: "p1", count: "126" },
      { value: "p2", count: "102" },
      { value: "p3", count: "71" },
      { value: "urgent", count: "24" },
      { value: "monitor", count: "13" },
    ],
  },
  {
    key: "region",
    description: "Geographic scope referenced by the case content.",
    count: "298",
    status: "stable",
    source: "facet",
    values: [
      { value: "east", count: "81" },
      { value: "north", count: "63" },
      { value: "south", count: "58" },
      { value: "shanghai", count: "49" },
      { value: "west", count: "47" },
    ],
  },
  {
    key: "review_stage",
    description: "Explicit review stage visible to operations.",
    count: "201",
    status: "review",
    source: "facet",
    values: [
      { value: "triage", count: "63" },
      { value: "review", count: "52" },
      { value: "escalated", count: "34" },
      { value: "blocked", count: "29" },
      { value: "closed", count: "23" },
    ],
  },
  {
    key: "policy_family",
    description: "Normalized policy family used in retrieval.",
    count: "163",
    status: "elevated",
    source: "facet",
    values: [
      { value: "appeal", count: "46" },
      { value: "coverage", count: "39" },
      { value: "exception", count: "31" },
      { value: "tax", count: "25" },
      { value: "claim", count: "22" },
    ],
  },
];

const semanticSchemaRows: SchemaEntry[] = [
  {
    key: "appeal_reason",
    description: "Open semantic reason phrases extracted from appeal cases.",
    count: "128",
    source: "semantic",
    values: [
      { value: "late filing", count: "22" },
      { value: "missing proof", count: "19" },
      { value: "penalty dispute", count: "17" },
      { value: "duplicate charge", count: "14" },
      { value: "manual override", count: "11" },
      { value: "form mismatch", count: "9" },
    ],
  },
  {
    key: "source_channel",
    description: "Source channel observed in incoming case material.",
    count: "94",
    source: "semantic",
    values: [
      { value: "portal", count: "28" },
      { value: "email", count: "24" },
      { value: "agent", count: "17" },
      { value: "internal sync", count: "14" },
      { value: "batch import", count: "11" },
    ],
  },
  {
    key: "exception_signal",
    description: "Emerging exception indicators not yet promoted into stable facet keys.",
    count: "86",
    source: "semantic",
    values: [
      { value: "manual escalation", count: "21" },
      { value: "missing annex", count: "18" },
      { value: "out of policy", count: "17" },
      { value: "rare jurisdiction", count: "16" },
      { value: "source ambiguity", count: "14" },
    ],
  },
  {
    key: "entity_name",
    description: "Named entities retained for retrieval expansion and answer synthesis.",
    count: "73",
    source: "semantic",
    values: [
      { value: "alpha corp", count: "18" },
      { value: "tax office east", count: "15" },
      { value: "delta hospital", count: "14" },
      { value: "city appeal board", count: "13" },
      { value: "north claims center", count: "13" },
    ],
  },
];

export function PartitionPage() {
  const [selectedEntry, setSelectedEntry] = useState<SchemaEntry | null>(null);

  const detailTitle = useMemo(() => {
    if (!selectedEntry) {
      return "Value List";
    }
    return `${selectedEntry.key}`;
  }, [selectedEntry]);

  return (
    <section className="partition-page">
      <header className="partition-page-header">
        <div className="partition-page-copy">
          <h2>Partition</h2>
          <p>Claims partition schema, semantic model, and complete key-value details.</p>
        </div>
      </header>

      <section className="partition-status-strip">
        {partitionSummary.map((item) => (
          <article key={item.label} className="partition-status-card">
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <small>{item.note}</small>
          </article>
        ))}
      </section>

      <section className="partition-workspace">
        <div className="partition-left-stack">
          <article className="skeleton-card partition-schema-card">
            <div className="partition-panel-head">
              <h3>Facet Schema</h3>
            </div>
            <div className="partition-schema-list-scroll">
              <div className="partition-schema-list">
                {facetSchemaRows.map((row) => {
                  const isActive = selectedEntry?.source === row.source && selectedEntry?.key === row.key;
                  return (
                    <button
                      key={row.key}
                      type="button"
                      className={`partition-schema-item${isActive ? " is-active" : ""}`}
                      onClick={() => setSelectedEntry(row)}
                    >
                      <div className="partition-schema-item-line">
                        <strong>{row.key}</strong>
                        <span>{row.count} cases</span>
                        <span>{row.values.length} values</span>
                        <span className={`partition-inline-status is-${row.status}`}>{row.status}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </article>

          <article className="skeleton-card partition-schema-card">
            <div className="partition-panel-head">
              <h3>Semantic Schema</h3>
            </div>
            <div className="partition-schema-list-scroll">
              <div className="partition-schema-list">
                {semanticSchemaRows.map((row) => {
                  const isActive = selectedEntry?.source === row.source && selectedEntry?.key === row.key;
                  return (
                    <button
                      key={row.key}
                      type="button"
                      className={`partition-schema-item${isActive ? " is-active" : ""}`}
                      onClick={() => setSelectedEntry(row)}
                    >
                      <div className="partition-schema-item-line">
                        <strong>{row.key}</strong>
                        <span>{row.count} cases</span>
                        <span>{row.values.length} values</span>
                        <span>{row.values[0]?.value ?? "-"}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </article>
        </div>

        <article className="skeleton-card partition-detail-card">
          <div className="partition-panel-head">
            <h3>{detailTitle}</h3>
            {selectedEntry ? (
              <span className="partition-inline-note">
                {selectedEntry.source === "facet" ? "Facet" : "Semantic"}
              </span>
            ) : null}
          </div>

          {selectedEntry ? (
            <div className="partition-detail-scroll">
              <div className="partition-detail-block">
                <p>{selectedEntry.description}</p>
                <div className="partition-detail-meta">
                  <span>{selectedEntry.count} cases</span>
                  <span>{selectedEntry.values.length} listed values</span>
                </div>
              </div>

              <div className="partition-value-table">
                <div className="partition-value-table-header">
                  <span>Value</span>
                  <span>Count</span>
                </div>
                {selectedEntry.values.map((item) => (
                  <div key={`${selectedEntry.key}:${item.value}`} className="partition-value-table-row">
                    <strong>{item.value}</strong>
                    <code>{item.count}</code>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="partition-empty-state">
              <strong>Click a key to inspect its value list.</strong>
              <p>Choose one item from Facet Schema or Semantic Schema to view all values and counts here.</p>
            </div>
          )}
        </article>
      </section>
    </section>
  );
}
