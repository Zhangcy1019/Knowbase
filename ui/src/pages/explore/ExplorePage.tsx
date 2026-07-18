import type { ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

import { IconExplore, IconMagnify, IconShrink, IconTraceDetail, IconTraceList } from "../../shared/icons";
import { getCase, listPartitionCases, type KnowbaseCaseDocument } from "../../shared/api";
import "./explore.css";

function PanelMark({ children }: { children: ReactNode }) {
  return <span className="explore-panel-mark">{children}</span>;
}

function formatTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function flattenFacets(facets: Record<string, string[]> | undefined) {
  return Object.entries(facets ?? {})
    .flatMap(([key, values]) => values.slice(0, 2).map((value) => `${key}:${value}`))
    .slice(0, 8);
}

function inferStatus(item: KnowbaseCaseDocument): "stable" | "review" | "elevated" {
  const status = item.metadata?.status || "";
  if (status === "archived") {
    return "review";
  }
  return "stable";
}

export function ExplorePage({ activePartition }: { activePartition: string | null }) {
  const [cases, setCases] = useState<KnowbaseCaseDocument[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [selectedCase, setSelectedCase] = useState<KnowbaseCaseDocument | null>(null);
  const [graphRatio, setGraphRatio] = useState(0.52);
  const [expandedPanel, setExpandedPanel] = useState<"graph" | "list" | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isPanelTransitioning, setIsPanelTransitioning] = useState(false);
  const [loadingCases, setLoadingCases] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const leftStackRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setIsPanelTransitioning(true);
    const timeoutId = window.setTimeout(() => {
      setIsPanelTransitioning(false);
    }, 240);
    return () => window.clearTimeout(timeoutId);
  }, [expandedPanel]);

  useEffect(() => {
    if (expandedPanel !== null) {
      return;
    }

    function onPointerMove(event: PointerEvent) {
      const container = leftStackRef.current;
      if (!container) {
        return;
      }
      if (event.buttons === 0) {
        return;
      }
      const rect = container.getBoundingClientRect();
      const splitterHeight = 8;
      const minGraphHeight = 220;
      const minListHeight = 220;
      const usableHeight = rect.height - splitterHeight;
      const pointerOffset = event.clientY - rect.top;
      const clampedGraphHeight = Math.min(
        usableHeight - minListHeight,
        Math.max(minGraphHeight, pointerOffset),
      );
      const nextRatio = clampedGraphHeight / usableHeight;
      setGraphRatio(Math.min(0.72, Math.max(0.28, nextRatio)));
    }

    function onPointerUp() {
      setIsDragging(false);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
    }

    function onDividerPointerDown(event: PointerEvent) {
      const target = event.target as HTMLElement | null;
      if (!target?.closest(".explore-splitter")) {
        return;
      }
      event.preventDefault();
      setIsDragging(true);
      window.addEventListener("pointermove", onPointerMove);
      window.addEventListener("pointerup", onPointerUp);
    }

    window.addEventListener("pointerdown", onDividerPointerDown);
    return () => {
      window.removeEventListener("pointerdown", onDividerPointerDown);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
    };
  }, [expandedPanel]);

  useEffect(() => {
    let cancelled = false;
    if (!activePartition?.trim()) {
      setCases([]);
      setSelectedCaseId("");
      setSelectedCase(null);
      setErrorMessage("");
      setLoadingCases(false);
      return () => {
        cancelled = true;
      };
    }
    setLoadingCases(true);
    setErrorMessage("");
    listPartitionCases(activePartition)
      .then((items) => {
        if (cancelled) {
          return;
        }
        setCases(items);
        setSelectedCaseId((current) => {
          if (current && items.some((item) => item.case_id === current)) {
            return current;
          }
          return items[0]?.case_id ?? "";
        });
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        setCases([]);
        setSelectedCaseId("");
        setSelectedCase(null);
        setErrorMessage(error instanceof Error ? error.message : "Failed to load cases.");
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingCases(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [activePartition]);

  useEffect(() => {
    let cancelled = false;
    if (!selectedCaseId) {
      setSelectedCase(null);
      setLoadingDetail(false);
      return () => {
        cancelled = true;
      };
    }
    setLoadingDetail(true);
    getCase(selectedCaseId)
      .then((item) => {
        if (!cancelled) {
          setSelectedCase(item);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setSelectedCase(null);
          setErrorMessage(error instanceof Error ? error.message : "Failed to load case detail.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingDetail(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedCaseId]);

  const leftStackStyle =
    expandedPanel === null
      ? ({
          gridTemplateRows: `minmax(220px, ${graphRatio}fr) 8px minmax(220px, ${1 - graphRatio}fr)`,
        } as const)
      : undefined;

  const selectedStatus = selectedCase ? inferStatus(selectedCase) : "stable";
  const selectedFacets = selectedCase ? flattenFacets(selectedCase.facets) : [];

  return (
    <section className="explore-page">
      <header className="explore-page-header">
        <div className="explore-page-copy">
          <h2>Explore</h2>
        </div>
      </header>

      <section className="explore-main-grid">
        <div
          ref={leftStackRef}
          className={`explore-left-stack${expandedPanel ? ` is-${expandedPanel}-expanded` : ""}${isDragging ? " is-dragging" : ""}${isPanelTransitioning ? " is-panel-transitioning" : ""}`}
          style={leftStackStyle}
        >
          {expandedPanel === "list" ? (
            <article className="skeleton-card explore-list-card is-solo">
              <div className="explore-panel-head">
                <div className="explore-panel-heading">
                  <PanelMark>
                    <IconTraceList />
                  </PanelMark>
                  <h3>Case List</h3>
                </div>
                <button
                  type="button"
                  className="explore-panel-toggle is-active"
                  onClick={() => setExpandedPanel(null)}
                  aria-label="Restore split view"
                >
                  <IconShrink />
                </button>
              </div>
              <div className="explore-list-scroll">
                <div className="explore-list-table">
                  <div className="explore-list-header">
                    <span>Case</span>
                    <span>Partition</span>
                    <span>Status</span>
                    <span>Updated</span>
                  </div>
                  {cases.map((item) => (
                    <button
                      key={item.case_id}
                      type="button"
                      className={`explore-list-row${selectedCaseId === item.case_id ? " is-active" : ""}`}
                      onClick={() => setSelectedCaseId(item.case_id)}
                    >
                      <strong>{item.title || item.case_id}</strong>
                      <span>{item.partition}</span>
                      <span className={`explore-inline-status is-${inferStatus(item)}`}>{inferStatus(item)}</span>
                      <span>{formatTime(item.updated_at)}</span>
                    </button>
                  ))}
                </div>
              </div>
            </article>
          ) : expandedPanel === "graph" ? (
            <article className="skeleton-card explore-graph-card is-solo">
              <div className="explore-panel-head">
                <div className="explore-panel-heading">
                  <PanelMark>
                    <IconExplore />
                  </PanelMark>
                  <h3>Graph</h3>
                </div>
                <button
                  type="button"
                  className="explore-panel-toggle is-active"
                  onClick={() => setExpandedPanel(null)}
                  aria-label="Restore split view"
                >
                  <IconShrink />
                </button>
              </div>
              <div className="explore-empty-state">
                <strong>Graph pending</strong>
              </div>
            </article>
          ) : (
            <>
              <article className="skeleton-card explore-graph-card">
                <div className="explore-panel-head">
                  <div className="explore-panel-heading">
                    <PanelMark>
                      <IconExplore />
                    </PanelMark>
                    <h3>Graph</h3>
                  </div>
                  <button
                    type="button"
                    className="explore-panel-toggle"
                    onClick={() => setExpandedPanel("graph")}
                    aria-label="Expand graph"
                  >
                    <IconMagnify />
                  </button>
                </div>
                <div className="explore-empty-state">
                  <strong>Graph pending</strong>
                </div>
              </article>

              <div className="explore-splitter" aria-hidden="true">
                <span />
              </div>

              <article className="skeleton-card explore-list-card">
                <div className="explore-panel-head">
                  <div className="explore-panel-heading">
                    <PanelMark>
                      <IconTraceList />
                    </PanelMark>
                    <h3>Case List</h3>
                  </div>
                  <button
                    type="button"
                    className="explore-panel-toggle"
                    onClick={() => setExpandedPanel("list")}
                    aria-label="Expand case list"
                  >
                    <IconMagnify />
                  </button>
                </div>
                <div className="explore-list-scroll">
                  <div className="explore-list-table">
                    {!activePartition ? <div className="explore-empty-state"><strong>No active partition</strong></div> : null}
                    {loadingCases ? <div className="explore-empty-state"><strong>Loading...</strong></div> : null}
                    {!loadingCases && errorMessage ? <div className="explore-empty-state"><strong>{errorMessage}</strong></div> : null}
                    {!loadingCases && activePartition && !errorMessage && cases.length === 0 ? (
                      <div className="explore-empty-state"><strong>No cases</strong></div>
                    ) : null}
                    {cases.length > 0 ? (
                      <>
                        <div className="explore-list-header">
                          <span>Case</span>
                          <span>Partition</span>
                          <span>Status</span>
                          <span>Updated</span>
                        </div>
                        {cases.map((item) => (
                          <button
                            key={item.case_id}
                            type="button"
                            className={`explore-list-row${selectedCaseId === item.case_id ? " is-active" : ""}`}
                            onClick={() => setSelectedCaseId(item.case_id)}
                          >
                            <strong>{item.title || item.case_id}</strong>
                            <span>{item.partition}</span>
                            <span className={`explore-inline-status is-${inferStatus(item)}`}>{inferStatus(item)}</span>
                            <span>{formatTime(item.updated_at)}</span>
                          </button>
                        ))}
                      </>
                    ) : null}
                  </div>
                </div>
              </article>
            </>
          )}
        </div>

        <article className="skeleton-card explore-detail-card">
          <div className="explore-panel-head">
            <div className="explore-panel-heading">
              <PanelMark>
                <IconTraceDetail />
              </PanelMark>
              <h3>Case Detail</h3>
            </div>
          </div>
          <div className="explore-detail-scroll">
            {!selectedCase && !loadingDetail ? (
              <div className="explore-empty-state">
                <strong>Select a case</strong>
              </div>
            ) : null}
            {loadingDetail ? (
              <div className="explore-empty-state">
                <strong>Loading...</strong>
              </div>
            ) : null}
            {selectedCase ? (
              <>
                <div className="explore-detail-meta">
                  <span className={`explore-inline-status is-${selectedStatus}`}>{selectedStatus}</span>
                  <code>{selectedCase.case_id}</code>
                </div>
                <h4>{selectedCase.title || selectedCase.case_id}</h4>
                <p>{selectedCase.partition}</p>
                <dl className="explore-detail-grid">
                  <div>
                    <dt>Partition</dt>
                    <dd>{selectedCase.partition}</dd>
                  </div>
                  <div>
                    <dt>Status</dt>
                    <dd>{selectedCase.metadata?.status || "--"}</dd>
                  </div>
                  <div>
                    <dt>Source</dt>
                    <dd>{selectedCase.metadata?.source || "--"}</dd>
                  </div>
                  <div>
                    <dt>Updated</dt>
                    <dd>{formatTime(selectedCase.updated_at)}</dd>
                  </div>
                </dl>
                <div className="explore-facet-row">
                  {selectedFacets.length === 0 ? <span>no facets</span> : null}
                  {selectedFacets.map((facet) => (
                    <span key={facet}>{facet}</span>
                  ))}
                </div>
              </>
            ) : null}
          </div>
        </article>
      </section>
    </section>
  );
}
