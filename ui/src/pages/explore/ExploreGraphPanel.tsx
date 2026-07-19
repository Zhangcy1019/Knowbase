import { IconExplore, IconMagnify, IconShrink } from "../../shared/icons";
import { PanelMark } from "./explore_shared";

type ExploreGraphPanelProps = {
  expanded: boolean;
  solo: boolean;
  onExpand: () => void;
  onRestore: () => void;
};

export function ExploreGraphPanel({ expanded, solo, onExpand, onRestore }: ExploreGraphPanelProps) {
  if (solo) {
    return (
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
            onClick={onRestore}
            aria-label="Restore split view"
          >
            <IconShrink />
          </button>
        </div>
        <div className="explore-empty-state">
          <strong>Graph pending</strong>
        </div>
      </article>
    );
  }

  return (
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
          className={`explore-panel-toggle${expanded ? " is-active" : ""}`}
          onClick={expanded ? onRestore : onExpand}
          aria-label={expanded ? "Restore split view" : "Expand graph"}
        >
          {expanded ? <IconShrink /> : <IconMagnify />}
        </button>
      </div>
      <div className="explore-empty-state">
        <strong>Graph pending</strong>
      </div>
    </article>
  );
}
