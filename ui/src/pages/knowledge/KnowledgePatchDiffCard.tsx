type KnowledgePatchDiffCardProps = {
  onOpen: (title: string, description: string, payload: unknown) => void;
  payload: unknown;
};

export function KnowledgePatchDiffCard({ onOpen }: KnowledgePatchDiffCardProps) {
  return (
    <button
      type="button"
      className="knowledge-process-item"
      onClick={() => onOpen("Patch Diff", "Auditable file-level change before apply.", payload)}
    >
      <span className="knowledge-process-number">03</span>
      <span className="knowledge-process-copy">
        <strong>Patch Diff</strong>
        <small>Auditable file-level change before apply.</small>
      </span>
      <span className="knowledge-process-open">Open</span>
    </button>
  );
}
