import type { MouseEvent } from "react";
import { useEffect, useRef, useState } from "react";

import {
  deleteCase,
  getCase,
  listPartitionCases,
  updateCase,
  type KnowbaseCaseDocument,
} from "../../shared/api";
import { rebuildCase } from "../../shared/api/runtime_runs";
import { ExploreCaseDetailPanel } from "./ExploreCaseDetailPanel";
import { ExploreCaseListPanel } from "./ExploreCaseListPanel";
import { ExploreGraphPanel } from "./ExploreGraphPanel";
import "./explore.css";

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
  const [refreshingSummary, setRefreshingSummary] = useState(false);
  const [savingCase, setSavingCase] = useState(false);
  const [deletingCaseId, setDeletingCaseId] = useState("");
  const [deleteConfirmCaseId, setDeleteConfirmCaseId] = useState("");
  const [deletePopoverPosition, setDeletePopoverPosition] = useState<{ top: number; left: number } | null>(null);
  const [listErrorMessage, setListErrorMessage] = useState("");
  const [detailErrorMessage, setDetailErrorMessage] = useState("");
  const [deleteErrorMessage, setDeleteErrorMessage] = useState("");
  const leftStackRef = useRef<HTMLDivElement | null>(null);
  const deletePopoverRef = useRef<HTMLDivElement | null>(null);

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
      setListErrorMessage("");
      setDetailErrorMessage("");
      setDeleteErrorMessage("");
      setLoadingCases(false);
      return () => {
        cancelled = true;
      };
    }
    setLoadingCases(true);
    setListErrorMessage("");
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
        setListErrorMessage(error instanceof Error ? error.message : "Failed to load cases.");
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
    setDetailErrorMessage("");
    getCase(selectedCaseId)
      .then((item) => {
        if (!cancelled) {
          setSelectedCase(item);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setSelectedCase(null);
          setDetailErrorMessage(error instanceof Error ? error.message : "Failed to load case detail.");
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

  useEffect(() => {
    if (!deleteConfirmCaseId) {
      setDeletePopoverPosition(null);
      return;
    }

    function handlePointerDown(event: PointerEvent) {
      const target = event.target as HTMLElement | null;
      if (!target) {
        return;
      }
      if (deletePopoverRef.current?.contains(target)) {
        return;
      }
      if (target.closest(`[data-case-delete-trigger="${deleteConfirmCaseId}"]`)) {
        return;
      }
      setDeleteConfirmCaseId("");
      setDeleteErrorMessage("");
    }

    function handleWindowResize() {
      setDeleteConfirmCaseId("");
      setDeleteErrorMessage("");
    }

    window.addEventListener("pointerdown", handlePointerDown);
    window.addEventListener("resize", handleWindowResize);
    window.addEventListener("scroll", handleWindowResize, true);
    return () => {
      window.removeEventListener("pointerdown", handlePointerDown);
      window.removeEventListener("resize", handleWindowResize);
      window.removeEventListener("scroll", handleWindowResize, true);
    };
  }, [deleteConfirmCaseId]);

  async function handleDeleteCase(caseId: string) {
    if (!caseId || deletingCaseId) {
      return;
    }
    setDeletingCaseId(caseId);
    setDeleteErrorMessage("");
    try {
      await deleteCase(caseId);
      setCases((current) => {
        const next = current.filter((item) => item.case_id !== caseId);
        setSelectedCaseId((currentSelected) => {
          if (currentSelected !== caseId) {
            return currentSelected;
          }
          return next[0]?.case_id ?? "";
        });
        return next;
      });
      if (selectedCaseId === caseId) {
        setSelectedCase(null);
      }
      setDeleteConfirmCaseId("");
    } catch (error: unknown) {
      setDeleteErrorMessage(error instanceof Error ? error.message : "Failed to delete case.");
    } finally {
      setDeletingCaseId("");
    }
  }

  async function handleRefreshSummary() {
    if (!selectedCase || refreshingSummary) {
      return;
    }
    setRefreshingSummary(true);
    setDetailErrorMessage("");
    try {
      await rebuildCase(selectedCase.case_id, selectedCase.partition);
      const refreshed = await getCase(selectedCase.case_id);
      setSelectedCase(refreshed);
      setCases((current) =>
        current.map((item) => (item.case_id === refreshed.case_id ? refreshed : item)),
      );
    } catch (error: unknown) {
      setDetailErrorMessage(error instanceof Error ? error.message : "Failed to refresh summary.");
    } finally {
      setRefreshingSummary(false);
    }
  }

  async function handleSaveCase(payload: { title: string; sourceContent: string }) {
    if (!selectedCase || savingCase) {
      return;
    }
    setSavingCase(true);
    setDetailErrorMessage("");
    try {
      const updated = await updateCase(selectedCase.case_id, {
        title: payload.title,
        source_content: payload.sourceContent,
      });
      setSelectedCase(updated);
      setCases((current) =>
        current.map((item) => (item.case_id === updated.case_id ? updated : item)),
      );
    } catch (error: unknown) {
      setDetailErrorMessage(error instanceof Error ? error.message : "Failed to save case.");
    } finally {
      setSavingCase(false);
    }
  }

  function toggleDeletePopover(caseId: string, event: MouseEvent<HTMLButtonElement>) {
    event.stopPropagation();
    if (deleteConfirmCaseId === caseId) {
      setDeleteConfirmCaseId("");
      setDeleteErrorMessage("");
      return;
    }
    const rect = event.currentTarget.getBoundingClientRect();
    setDeletePopoverPosition({
      top: rect.top - 10,
      left: Math.max(12, rect.right - 280),
    });
    setDeleteConfirmCaseId(caseId);
    setDeleteErrorMessage("");
  }

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
        </div>
      </header>

      <section className="explore-main-grid">
        <div
          ref={leftStackRef}
          className={`explore-left-stack${expandedPanel ? ` is-${expandedPanel}-expanded` : ""}${isDragging ? " is-dragging" : ""}${isPanelTransitioning ? " is-panel-transitioning" : ""}`}
          style={leftStackStyle}
        >
          {expandedPanel === "list" ? (
            <ExploreCaseListPanel
              cases={cases}
              activePartition={activePartition}
              selectedCaseId={selectedCaseId}
              loadingCases={loadingCases}
              listErrorMessage={listErrorMessage}
              deleteErrorMessage={deleteErrorMessage}
              expanded
              solo
              deleteConfirmCaseId={deleteConfirmCaseId}
              deletingCaseId={deletingCaseId}
              deletePopoverPosition={deletePopoverPosition}
              deletePopoverRef={deletePopoverRef}
              onSelectCase={setSelectedCaseId}
              onToggleDelete={toggleDeletePopover}
              onCancelDelete={() => {
                setDeleteConfirmCaseId("");
                setDeleteErrorMessage("");
              }}
              onConfirmDelete={(caseId) => void handleDeleteCase(caseId)}
              onExpand={() => setExpandedPanel("list")}
              onRestore={() => setExpandedPanel(null)}
            />
          ) : expandedPanel === "graph" ? (
            <ExploreGraphPanel expanded solo onExpand={() => setExpandedPanel("graph")} onRestore={() => setExpandedPanel(null)} />
          ) : (
            <>
              <ExploreGraphPanel expanded={expandedPanel === "graph"} solo={false} onExpand={() => setExpandedPanel("graph")} onRestore={() => setExpandedPanel(null)} />

              <div className="explore-splitter" aria-hidden="true">
                <span />
              </div>

              <ExploreCaseListPanel
                cases={cases}
                activePartition={activePartition}
                selectedCaseId={selectedCaseId}
                loadingCases={loadingCases}
                listErrorMessage={listErrorMessage}
                deleteErrorMessage={deleteErrorMessage}
                expanded={expandedPanel === "list"}
                solo={false}
                deleteConfirmCaseId={deleteConfirmCaseId}
                deletingCaseId={deletingCaseId}
                deletePopoverPosition={deletePopoverPosition}
                deletePopoverRef={deletePopoverRef}
                onSelectCase={setSelectedCaseId}
                onToggleDelete={toggleDeletePopover}
                onCancelDelete={() => {
                  setDeleteConfirmCaseId("");
                  setDeleteErrorMessage("");
                }}
                onConfirmDelete={(caseId) => void handleDeleteCase(caseId)}
                onExpand={() => setExpandedPanel("list")}
                onRestore={() => setExpandedPanel(null)}
              />
            </>
          )}
        </div>

        <ExploreCaseDetailPanel
          selectedCase={selectedCase}
          loadingDetail={loadingDetail}
          savingCase={savingCase}
          detailErrorMessage={detailErrorMessage}
          onSaveCase={(payload) => void handleSaveCase(payload)}
        />
      </section>
    </section>
  );
}
