import { IconQuery } from "../../shared/icons";

export type PartitionSchemaEntry = {
  key: string;
  description: string;
  count: number;
  values: Array<{ value: string; count: number }>;
  status?: "stable" | "review" | "elevated";
  source: "facet" | "semantic" | "query";
};

export function PartitionQuerySignals({
  rows,
  selectedEntry,
  onSelect,
  loading,
}: {
  rows: PartitionSchemaEntry[];
  selectedEntry: PartitionSchemaEntry | null;
  onSelect: (entry: PartitionSchemaEntry) => void;
  loading: boolean;
}) {
  return (
    <article className="skeleton-card partition-schema-card partition-query-signals-card">
      <div className="partition-panel-head">
        <div className="partition-panel-heading">
          <span className="partition-panel-mark"><IconQuery /></span>
          <h3>Query Signals</h3>
        </div>
        <span className="partition-inline-note">{rows.length}</span>
      </div>
      <div className="partition-schema-list-scroll">
        <div className="partition-schema-list">
          {!loading && rows.length === 0 ? (
            <div className="partition-empty-state">
              <strong>No query signals</strong>
              <p>Query-derived statistics will appear here after searches accumulate.</p>
            </div>
          ) : null}
          {rows.map((row) => {
            const isActive = selectedEntry?.source === row.source && selectedEntry?.key === row.key;
            return (
              <button
                key={row.key}
                type="button"
                className={`partition-schema-item${isActive ? " is-active" : ""}`}
                onClick={() => onSelect(row)}
              >
                <div className="partition-schema-item-line">
                  <strong>{row.key}</strong>
                  <span>{row.count} queries</span>
                  <span>{row.values.length} values</span>
                  <span>{row.values[0]?.value ?? "-"}</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </article>
  );
}
