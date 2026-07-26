export type BacklogResourceTab = "events" | "tasks";

type BacklogResourceTabsProps = {
  activeTab: BacklogResourceTab;
  onChange: (tab: BacklogResourceTab) => void;
};

export function BacklogResourceTabs({ activeTab, onChange }: BacklogResourceTabsProps) {
  return (
    <div className="backlog-resource-tabs" role="tablist" aria-label="Backlog resources">
      <button
        type="button"
        role="tab"
        aria-selected={activeTab === "events"}
        className={activeTab === "events" ? "is-active" : ""}
        onClick={() => onChange("events")}
      >
        Events
        <span>durable records</span>
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={activeTab === "tasks"}
        className={activeTab === "tasks" ? "is-active" : ""}
        onClick={() => onChange("tasks")}
      >
        Tasks
        <span>live queue</span>
      </button>
    </div>
  );
}
