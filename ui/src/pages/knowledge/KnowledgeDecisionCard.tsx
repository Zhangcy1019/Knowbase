type KnowledgeDecisionCardProps = {
  onOpen: (title: string, description: string, payload: unknown) => void;
  payload: unknown;
};

export function KnowledgeDecisionCard({ onOpen, payload }: KnowledgeDecisionCardProps) {
  return (
    <button
      type="button"
      className="knowledge-process-item"
      onClick={() => onOpen("Decision", "Facet governance conclusion and rationale.", payload)}
    >
      <span className="knowledge-process-number">01</span>
      <span className="knowledge-process-copy">
        <strong>Decision</strong>
        <small>Facet governance conclusion and rationale.</small>
      </span>
      <span className="knowledge-process-open">Open</span>
    </button>
  );
}
