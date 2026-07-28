export type KnowledgeFlowMetric = {
  label: string;
  value: string;
};

type KnowledgeFlowCardProps = {
  index: string;
  title: string;
  kicker: string;
  status: string;
  tone?: "good" | "review" | "failed" | "idle";
  summary: string;
  method?: string;
  metrics: KnowledgeFlowMetric[];
  onOpen: () => void;
};

export function KnowledgeFlowCard({
  index,
  title,
  kicker,
  status,
  tone = "idle",
  summary,
  method,
  metrics,
  onOpen,
}: KnowledgeFlowCardProps) {
  return (
    <button type="button" className={`knowledge-flow-card is-${tone}`} onClick={onOpen}>
      <div className="knowledge-flow-card-head">
        <span className="knowledge-flow-index">{index}</span>
        <div className="knowledge-flow-heading">
          <span className="knowledge-flow-kicker">{kicker}</span>
          <strong>{title}</strong>
        </div>
        <span className="knowledge-flow-status">{status}</span>
      </div>
      <p className="knowledge-flow-summary">{summary}</p>
      {method ? <p className="knowledge-flow-method"><strong>How it is calculated:</strong> {method}</p> : null}
      <div className="knowledge-flow-metrics">
        {metrics.map((metric) => (
          <span className="knowledge-flow-metric" key={metric.label}>
            <small>{metric.label}</small>
            <strong>{metric.value}</strong>
          </span>
        ))}
      </div>
      <span className="knowledge-flow-open">Open stage details <span aria-hidden="true">→</span></span>
    </button>
  );
}
