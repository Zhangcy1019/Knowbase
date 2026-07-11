const PAGE_TITLES: Record<string, string> = {
  "/overview": "Overview",
  "/explore": "Explore",
  "/backlog": "Backlog",
  "/runs": "Runs",
  "/settings": "Settings",
  "/design": "Design",
};

export function Topbar({ pathname }: { pathname: string }) {
  const title = PAGE_TITLES[pathname] ?? "Overview";

  return (
    <header className="app-topbar">
      <div>
        <h1>{title}</h1>
      </div>
      <div className="app-topbar-actions">
        <div className="context-chip">
          <span>Mode</span>
          <strong>Design Skeleton</strong>
        </div>
        <button type="button" className="ghost-button">
          Create Partition
        </button>
      </div>
    </header>
  );
}
