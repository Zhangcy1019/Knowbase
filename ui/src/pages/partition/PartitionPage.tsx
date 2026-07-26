import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import "./partition.css";
import { IconPartition, IconQuery, IconTraceDetail } from "../../shared/icons";
import {
  getPartition,
  getPartitionFacetSchema,
  getPartitionSemanticIndex,
  getPartitionQueryStatistics,
  getPartitionCaseStatistics,
  type PartitionFacetDefinition,
  type PartitionSemanticKeyStat,
  type PartitionQueryStatistics,
  type PartitionCaseStatistics,
} from "../../shared/api";
import { PartitionQuerySignals, type PartitionSchemaEntry } from "./PartitionQuerySignals";

type SchemaEntry = PartitionSchemaEntry;

function PanelMark({ children }: { children: ReactNode }) {
  return <span className="partition-panel-mark">{children}</span>;
}

function buildFacetRows(definitions: PartitionFacetDefinition[], statistics: PartitionCaseStatistics): SchemaEntry[] {
  return definitions.map((definition) => {
    const keyRef = `facet:${definition.key}`;
    const values = Object.entries(statistics.case_value_stats[keyRef] ?? {})
      .sort((left, right) => right[1] - left[1])
      .slice(0, 8)
      .map(([value, count]) => ({ value, count }));
    return {
      key: definition.key,
      description: definition.description || definition.display_name || definition.key,
      count: statistics.case_key_stats[keyRef] ?? 0,
      values,
      status: definition.enabled ? "stable" : "review",
      source: "facet",
    };
  });
}

function buildSemanticRows(indexStats: PartitionSemanticKeyStat[], statistics: PartitionCaseStatistics): SchemaEntry[] {
  const aliases = new Map(indexStats.map((item) => [item.key, item.aliases]));
  return Object.entries(statistics.case_key_stats)
    .filter(([key]) => key.startsWith("semantic_profile:"))
    .map(([key, count]) => {
      const semanticKey = key.slice("semantic_profile:".length);
      return {
        key: semanticKey,
        description: aliases.get(semanticKey)?.join(", ") || semanticKey,
        count,
        values: Object.entries(statistics.case_value_stats[key] ?? {})
          .sort((left, right) => right[1] - left[1])
          .slice(0, 8)
          .map(([value, valueCount]) => ({ value, count: valueCount })),
        source: "semantic" as const,
      };
    })
    .sort((left, right) => right.count - left.count);
}

function buildQueryRows(statistics: PartitionQueryStatistics | null): SchemaEntry[] {
  if (!statistics) return [];
  return Object.entries(statistics.query_key_stats)
    .map(([key, count]) => ({
      key,
      description: "Query-derived signal. This statistic does not change the partition schema.",
      count,
      values: Object.entries(statistics.query_value_stats[key] ?? {})
        .sort((left, right) => right[1] - left[1])
        .slice(0, 8)
        .map(([value, valueCount]) => ({ value, count: valueCount })),
      source: "query" as const,
    }))
    .sort((left, right) => right.count - left.count);
}

export function PartitionPage({ activePartition }: { activePartition: string | null }) {
  const [facetRows, setFacetRows] = useState<SchemaEntry[]>([]);
  const [semanticRows, setSemanticRows] = useState<SchemaEntry[]>([]);
  const [selectedEntry, setSelectedEntry] = useState<SchemaEntry | null>(null);
  const [partitionDescription, setPartitionDescription] = useState("");
  const [partitionStatus, setPartitionStatus] = useState("");
  const [queryStatistics, setQueryStatistics] = useState<PartitionQueryStatistics | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    if (!activePartition?.trim()) {
      setFacetRows([]);
      setSemanticRows([]);
      setSelectedEntry(null);
      setPartitionDescription("");
      setPartitionStatus("");
      setQueryStatistics(null);
      setErrorMessage("");
      setLoading(false);
      return () => {
        cancelled = true;
      };
    }
    setLoading(true);
    setErrorMessage("");
    Promise.all([
      getPartition(activePartition),
      getPartitionFacetSchema(activePartition),
      getPartitionSemanticIndex(activePartition),
      getPartitionCaseStatistics(activePartition),
      getPartitionQueryStatistics(activePartition),
    ])
      .then(([partition, facetSchema, semanticIndex, caseStats, queryStats]) => {
        if (cancelled) {
          return;
        }
        const nextFacetRows = buildFacetRows(facetSchema.facet_schema.definitions, caseStats);
        const nextSemanticRows = buildSemanticRows(semanticIndex.semantic_index.key_stats, caseStats);
        setPartitionDescription(partition.scenario_description || "");
        setPartitionStatus(partition.status || "");
        setQueryStatistics(queryStats);
        setFacetRows(nextFacetRows);
        setSemanticRows(nextSemanticRows);
        setSelectedEntry((current) => {
          if (!current) {
            return nextFacetRows[0] ?? nextSemanticRows[0] ?? null;
          }
          return [...nextFacetRows, ...nextSemanticRows].find(
            (item) => item.source === current.source && item.key === current.key,
          ) ?? nextFacetRows[0] ?? nextSemanticRows[0] ?? null;
        });
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        setFacetRows([]);
        setSemanticRows([]);
        setSelectedEntry(null);
        setPartitionDescription("");
        setPartitionStatus("");
        setQueryStatistics(null);
        setErrorMessage(error instanceof Error ? error.message : "Failed to load partition.");
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [activePartition]);

  const detailTitle = useMemo(() => selectedEntry?.key || "Value List", [selectedEntry]);
  const queryRows = buildQueryRows(queryStatistics);
  return (
    <section className="partition-page">
      <header className="partition-page-header">
        <div className="partition-page-copy">
          <div className="partition-title-line">
            <h2>{activePartition || "Partition"}</h2>
            {partitionStatus ? <span className={"partition-inline-status is-" + partitionStatus}>{partitionStatus}</span> : null}
          </div>
          {partitionDescription ? <p>{partitionDescription}</p> : null}
        </div>
      </header>

      <section className="partition-workspace">
        <div className="partition-left-stack">
          <article className="skeleton-card partition-schema-card">
            <div className="partition-panel-head">
              <div className="partition-panel-heading">
                <PanelMark>
                  <IconPartition />
                </PanelMark>
                <h3>Facet Schema</h3>
              </div>
              <span className="partition-inline-note">{facetRows.length}</span>
            </div>
            <div className="partition-schema-list-scroll">
              <div className="partition-schema-list">
                {!activePartition ? <div className="partition-empty-state"><strong>No active partition</strong></div> : null}
                {loading ? <div className="partition-empty-state"><strong>Loading...</strong></div> : null}
                {!loading && errorMessage ? <div className="partition-empty-state"><strong>{errorMessage}</strong></div> : null}
                {!loading && !errorMessage && activePartition && facetRows.length === 0 ? (
                  <div className="partition-empty-state"><strong>No facet keys</strong></div>
                ) : null}
                {facetRows.map((row) => {
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
              <div className="partition-panel-heading">
                <PanelMark>
                  <IconQuery />
                </PanelMark>
                <h3>Semantic Schema</h3>
              </div>
              <span className="partition-inline-note">{semanticRows.length}</span>
            </div>
            <div className="partition-schema-list-scroll">
              <div className="partition-schema-list">
                {!activePartition ? (
                  <div className="partition-empty-state">
                    <strong>No active partition</strong>
                  </div>
                ) : null}
                {loading ? (
                  <div className="partition-empty-state">
                    <strong>Loading...</strong>
                    <p>Reading semantic key statistics for this partition.</p>
                  </div>
                ) : null}
                {!loading && errorMessage ? (
                  <div className="partition-empty-state">
                    <strong>{errorMessage}</strong>
                    <p>Semantic schema could not be loaded.</p>
                  </div>
                ) : null}
                {!loading && !errorMessage && activePartition && semanticRows.length === 0 ? (
                  <div className="partition-empty-state">
                    <strong>No semantic keys</strong>
                    <p>Semantic values will appear here after cases accumulate.</p>
                  </div>
                ) : null}
                {semanticRows.map((row) => {
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

          <PartitionQuerySignals
            rows={queryRows}
            selectedEntry={selectedEntry}
            onSelect={setSelectedEntry}
            loading={loading}
          />
        </div>

        <article className="skeleton-card partition-detail-card">
          <div className="partition-panel-head">
            <div className="partition-panel-heading">
              <PanelMark>
                <IconTraceDetail />
              </PanelMark>
              <h3>{detailTitle}</h3>
            </div>
            {selectedEntry ? (
              <span className="partition-inline-note">
                {selectedEntry.source === "facet" ? "Facet" : selectedEntry.source === "semantic" ? "Semantic" : "Query"}
              </span>
            ) : null}
          </div>

          {selectedEntry ? (
            <div className="partition-detail-scroll">
              <div className="partition-detail-block">
                <p>{selectedEntry.description}</p>
                <div className="partition-detail-meta">
                  <span>{selectedEntry.count} {selectedEntry.source === "query" ? "queries" : "cases"}</span>
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
              <strong>Select a key to inspect values.</strong>
            </div>
          )}
        </article>
      </section>
    </section>
  );
}
