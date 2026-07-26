type KnowledgeAuditRuntimeCardProps = {
  onOpen: (title: string, description: string, payload: unknown) => void;
  payload: unknown;
};

export function KnowledgeAuditRuntimeCard({ onOpen, payload }: KnowledgeAuditRuntimeCardProps) {
  return (
    <button
      type="button"
      className="knowledge-process-item"
      onClick={() => onOpen("Audit / Runtime", "Linked task, run, and execution records.", payload)}
    >
      <span className="knowledge-process-number">04</span>
      <span className="knowledge-process-copy">
        <strong>Audit / Runtime</strong>
        <small>Linked task, run, and execution records.</small>
      </span>
      <span className="knowledge-process-open">Open</span>
    </button>
  );
}
