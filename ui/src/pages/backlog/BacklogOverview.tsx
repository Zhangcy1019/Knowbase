type BacklogOverviewProps = {
  total: number;
  pending: number;
  failed: number;
  completed: number;
};

export function BacklogOverview({ total, pending, failed, completed }: BacklogOverviewProps) {
  return (
    <section className="backlog-overview" aria-label="Event queue overview">
      <div className="backlog-overview-title">Event queue</div>
      <div className="backlog-overview-metrics">
        <div className="backlog-overview-metric">
          <span>Total events</span>
          <strong>{total}</strong>
        </div>
        <div className="backlog-overview-metric is-pending">
          <span>Pending events</span>
          <strong>{pending}</strong>
        </div>
        <div className="backlog-overview-metric is-failed">
          <span>Failed events</span>
          <strong>{failed}</strong>
        </div>
        <div className="backlog-overview-metric is-completed">
          <span>Completed events</span>
          <strong>{completed}</strong>
        </div>
      </div>
    </section>
  );
}
