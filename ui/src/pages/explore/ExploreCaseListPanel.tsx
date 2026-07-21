import type { MouseEvent } from "react";
import type { RefObject } from "react";

import { ConfirmDeletePopover } from "../../shared/component/confirm";
import { IconDelete, IconMagnify, IconShrink, IconTraceList } from "../../shared/icons";
import type { KnowbaseCaseDocument } from "../../shared/api";
import { formatDateTime, inferStatus, PanelMark } from "./explore_shared";

type ExploreCaseListPanelProps = {
  cases: KnowbaseCaseDocument[];
  activePartition: string | null;
  selectedCaseId: string;
  loadingCases: boolean;
  listErrorMessage: string;
  deleteErrorMessage: string;
  expanded: boolean;
  solo: boolean;
  deleteConfirmCaseId: string;
  deletingCaseId: string;
  deletePopoverPosition: { top: number; left: number } | null;
  deletePopoverRef: RefObject<HTMLDivElement | null>;
  onSelectCase: (caseId: string) => void;
  onToggleDelete: (caseId: string, event: MouseEvent<HTMLButtonElement>) => void;
  onCancelDelete: () => void;
  onConfirmDelete: (caseId: string) => void;
  onExpand: () => void;
  onRestore: () => void;
};

export function ExploreCaseListPanel({
  cases,
  activePartition,
  selectedCaseId,
  loadingCases,
  listErrorMessage,
  deleteErrorMessage,
  expanded,
  solo,
  deleteConfirmCaseId,
  deletingCaseId,
  deletePopoverPosition,
  deletePopoverRef,
  onSelectCase,
  onToggleDelete,
  onCancelDelete,
  onConfirmDelete,
  onExpand,
  onRestore,
}: ExploreCaseListPanelProps) {
  return (
    <article className={`skeleton-card explore-list-card${solo ? " is-solo" : ""}`}>
      <div className="explore-panel-head">
        <div className="explore-panel-heading">
          <PanelMark>
            <IconTraceList />
          </PanelMark>
          <h3>Case List</h3>
        </div>
        <button
          type="button"
          className={`explore-panel-toggle${expanded ? " is-active" : ""}`}
          onClick={expanded ? onRestore : onExpand}
          aria-label={expanded ? "Restore split view" : "Expand case list"}
        >
          {expanded ? <IconShrink /> : <IconMagnify />}
        </button>
      </div>
      <div className="explore-list-scroll">
        <div className="explore-list-table">
          {!solo && !activePartition ? <div className="explore-empty-state"><strong>No active partition</strong></div> : null}
          {!solo && loadingCases ? <div className="explore-empty-state"><strong>Loading...</strong></div> : null}
          {!solo && !loadingCases && listErrorMessage ? <div className="explore-empty-state"><strong>{listErrorMessage}</strong></div> : null}
          {!solo && !loadingCases && activePartition && !listErrorMessage && cases.length === 0 ? (
            <div className="explore-empty-state"><strong>No cases</strong></div>
          ) : null}

          {cases.length > 0 ? (
            <>
              <div className="explore-list-header">
                <span>Case</span>
                <span>Partition</span>
                <span>Status</span>
                <span>Updated</span>
                <span />
              </div>
              {cases.map((item) => (
                <div
                  key={item.case_id}
                  className={`explore-list-row${selectedCaseId === item.case_id ? " is-active" : ""}`}
                  onClick={() => onSelectCase(item.case_id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelectCase(item.case_id);
                    }
                  }}
                >
                  <strong>{item.title || item.case_id}</strong>
                  <span>{item.partition}</span>
                  <span className={`explore-inline-status is-${inferStatus(item)}`}>{inferStatus(item)}</span>
                  <span>{formatDateTime(item.updated_at)}</span>
                  <div className="explore-list-row-action">
                    <button
                      type="button"
                      className="explore-list-delete"
                      onClick={(event) => onToggleDelete(item.case_id, event)}
                      disabled={deletingCaseId === item.case_id}
                      aria-label="Delete case"
                      data-case-delete-trigger={item.case_id}
                    >
                      <IconDelete />
                    </button>
                    {deleteConfirmCaseId === item.case_id && deletePopoverPosition ? (
                      <ConfirmDeletePopover
                        ref={deletePopoverRef}
                        className="explore-delete-popover"
                        style={{
                          top: deletePopoverPosition.top,
                          left: deletePopoverPosition.left,
                          transform: "translateY(-100%)",
                        }}
                        title={`Delete ${item.title || item.case_id}?`}
                        description="This will remove the case from the active partition."
                        errorMessage={deleteErrorMessage}
                        pending={deletingCaseId === item.case_id}
                        onCancel={onCancelDelete}
                        onConfirm={() => onConfirmDelete(item.case_id)}
                      />
                    ) : null}
                  </div>
                </div>
              ))}
            </>
          ) : null}
        </div>
      </div>
    </article>
  );
}
