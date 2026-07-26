type KnowledgeMutationPlanCardProps = {
  onOpen: (title: string, description: string, payload: unknown) => void;
  payload: unknown;
};

export function KnowledgeMutationPlanCard({ onOpen, payload }: KnowledgeMutationPlanCardProps) {
  return (
    <button
      type="button"
      className="knowledge-process-item"
      onClick={() => onOpen("Mutation Plan", "Proposed schema and case projection changes.", payload)}
    >
      <span className="knowledge-process-number">02</span>
      <span className="knowledge-process-copy">
        <strong>Mutation Plan</strong>
        <small>Proposed schema and case projection changes.</small>
      </span>
      <span className="knowledge-process-open">Open</span>
    </button>
  );
}
