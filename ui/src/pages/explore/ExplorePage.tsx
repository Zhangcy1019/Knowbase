import { useEffect, useMemo, useRef, useState } from "react";
import { IconMagnify } from "../../shared/icons/IconMagnify";
import { IconShrink } from "../../shared/icons/IconShrink";
import "./explore.css";

type ExploreCase = {
  id: string;
  title: string;
  type: "case" | "summary" | "procedure";
  topic: string;
  partition: string;
  status: "stable" | "review" | "elevated";
  updatedAt: string;
  summary: string;
  facets: string[];
};

const exploreCases: ExploreCase[] = [
  {
    id: "case-2014",
    title: "Tax penalty appeal",
    type: "case",
    topic: "Tax",
    partition: "Tax",
    status: "stable",
    updatedAt: "2m ago",
    summary: "Appeal handling, reference documents, and supporting procedure chain.",
    facets: ["Tax", "Appeal", "Penalty"],
  },
  {
    id: "case-2088",
    title: "Claims reassessment",
    type: "case",
    topic: "Claims",
    partition: "Claims",
    status: "elevated",
    updatedAt: "6m ago",
    summary: "Claims reassessment with pending backlog pressure and recent runtime activity.",
    facets: ["Claims", "Review", "Escalation"],
  },
  {
    id: "summary-190",
    title: "Policy summary",
    type: "summary",
    topic: "Policy",
    partition: "Policy",
    status: "review",
    updatedAt: "9m ago",
    summary: "Condensed policy view used by downstream retrieval and case enrichment.",
    facets: ["Policy", "Summary"],
  },
  {
    id: "procedure-77",
    title: "Finance procedure",
    type: "procedure",
    topic: "Finance",
    partition: "Finance",
    status: "stable",
    updatedAt: "14m ago",
    summary: "Procedure chain for finance intake, normalization, and case generation.",
    facets: ["Finance", "Procedure", "Ingest"],
  },
];

const graphNodes = [
  { id: "topic-tax", label: "Tax", kind: "topic" },
  { id: "topic-claims", label: "Claims", kind: "topic" },
  { id: "topic-policy", label: "Policy", kind: "topic" },
  { id: "case-2014", label: "Tax penalty appeal", kind: "case" },
  { id: "case-2088", label: "Claims reassessment", kind: "case" },
  { id: "summary-190", label: "Policy summary", kind: "summary" },
  { id: "procedure-77", label: "Finance procedure", kind: "procedure" },
] as const;

export function ExplorePage() {
  const [selectedCaseId, setSelectedCaseId] = useState("case-2088");
  const [graphRatio, setGraphRatio] = useState(0.52);
  const [expandedPanel, setExpandedPanel] = useState<"graph" | "list" | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isPanelTransitioning, setIsPanelTransitioning] = useState(false);
  const leftStackRef = useRef<HTMLDivElement | null>(null);

  const selectedCase = useMemo(
    () => exploreCases.find((item) => item.id === selectedCaseId) ?? exploreCases[0],
    [selectedCaseId],
  );

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

  const leftStackStyle =
    expandedPanel === null
      ? ({
          gridTemplateRows: `minmax(220px, ${graphRatio}fr) 8px minmax(220px, ${1 - graphRatio}fr)`,
        } as const)
      : undefined;

  return (
    <section className="explore-page">
      <header className="explore-page-header">
        <div className="explore-page-copy">
          <h2>Explore</h2>
          <p>Graph, case list, and detail stay linked in one workspace.</p>
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
                <h3>Case List</h3>
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
                  {exploreCases.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      className={`explore-list-row${selectedCaseId === item.id ? " is-active" : ""}`}
                      onClick={() => setSelectedCaseId(item.id)}
                    >
                      <strong>{item.title}</strong>
                      <span>{item.partition}</span>
                      <span className={`explore-inline-status is-${item.status}`}>{item.status}</span>
                      <span>{item.updatedAt}</span>
                    </button>
                  ))}
                </div>
              </div>
            </article>
          ) : expandedPanel === "graph" ? (
            <article className="skeleton-card explore-graph-card is-solo">
              <div className="explore-panel-head">
                <h3>Graph</h3>
                <button
                  type="button"
                  className="explore-panel-toggle is-active"
                  onClick={() => setExpandedPanel(null)}
                  aria-label="Restore split view"
                >
                  <IconShrink />
                </button>
              </div>
              <div className="explore-graph-stage">
                {graphNodes.map((node) => {
                  const relatedCase = exploreCases.find((item) => item.id === node.id);
                  const isActive = selectedCaseId === node.id;
                  const isInteractive = Boolean(relatedCase);
                  return (
                    <button
                      key={node.id}
                      type="button"
                      className={`explore-graph-node is-${node.kind}${isActive ? " is-active" : ""}`}
                      onClick={() => {
                        if (isInteractive) {
                          setSelectedCaseId(node.id);
                        }
                      }}
                      disabled={!isInteractive}
                    >
                      <span>{node.label}</span>
                    </button>
                  );
                })}
              </div>
            </article>
          ) : (
            <>
              <article className="skeleton-card explore-graph-card">
                <div className="explore-panel-head">
                  <h3>Graph</h3>
                  <button
                    type="button"
                    className="explore-panel-toggle"
                    onClick={() => setExpandedPanel("graph")}
                    aria-label="Expand graph"
                  >
                    <IconMagnify />
                  </button>
                </div>
                <div className="explore-graph-stage">
                  {graphNodes.map((node) => {
                    const relatedCase = exploreCases.find((item) => item.id === node.id);
                    const isActive = selectedCaseId === node.id;
                    const isInteractive = Boolean(relatedCase);
                    return (
                      <button
                        key={node.id}
                        type="button"
                        className={`explore-graph-node is-${node.kind}${isActive ? " is-active" : ""}`}
                        onClick={() => {
                          if (isInteractive) {
                            setSelectedCaseId(node.id);
                          }
                        }}
                        disabled={!isInteractive}
                      >
                        <span>{node.label}</span>
                      </button>
                    );
                  })}
                </div>
              </article>

              <div className="explore-splitter" aria-hidden="true">
                <span />
              </div>

              <article className="skeleton-card explore-list-card">
                <div className="explore-panel-head">
                  <h3>Case List</h3>
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
                    <div className="explore-list-header">
                      <span>Case</span>
                      <span>Partition</span>
                      <span>Status</span>
                      <span>Updated</span>
                    </div>
                    {exploreCases.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        className={`explore-list-row${selectedCaseId === item.id ? " is-active" : ""}`}
                        onClick={() => setSelectedCaseId(item.id)}
                      >
                        <strong>{item.title}</strong>
                        <span>{item.partition}</span>
                        <span className={`explore-inline-status is-${item.status}`}>{item.status}</span>
                        <span>{item.updatedAt}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </article>
            </>
          )}
        </div>

        <article className="skeleton-card explore-detail-card">
          <div className="explore-panel-head">
            <h3>Case Detail</h3>
          </div>
          <div className="explore-detail-scroll">
            <div className="explore-detail-meta">
              <span className={`explore-inline-status is-${selectedCase.status}`}>{selectedCase.status}</span>
              <code>{selectedCase.id}</code>
            </div>
            <h4>{selectedCase.title}</h4>
            <p>{selectedCase.summary}</p>
            <dl className="explore-detail-grid">
              <div>
                <dt>Partition</dt>
                <dd>{selectedCase.partition}</dd>
              </div>
              <div>
                <dt>Topic</dt>
                <dd>{selectedCase.topic}</dd>
              </div>
              <div>
                <dt>Type</dt>
                <dd>{selectedCase.type}</dd>
              </div>
              <div>
                <dt>Updated</dt>
                <dd>{selectedCase.updatedAt}</dd>
              </div>
            </dl>
            <div className="explore-facet-row">
              {selectedCase.facets.map((facet) => (
                <span key={facet}>{facet}</span>
              ))}
            </div>
          </div>
        </article>
      </section>
    </section>
  );
}
