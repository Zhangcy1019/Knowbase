import { withBasePath } from "../basePath";
import {
  IconBacklog,
  IconExplore,
  IconIngest,
  IconOverview,
  IconPartition,
  IconQuery,
  IconRuns,
  IconSettings,
  IconTraceLoop,
} from "../../shared/icons";

const navGroups = [
  {
    title: "Workspace",
    items: [
      { href: "/partition", label: "Partition", icon: IconPartition },
      { href: "/explore", label: "Explore", icon: IconExplore },
      { href: "/query", label: "Query", icon: IconQuery },
      { href: "/ingest", label: "Ingest", icon: IconIngest },
      { href: "/backlog", label: "Backlog", icon: IconBacklog },
      { href: "/knowledge", label: "Knowledge", icon: IconTraceLoop },
      { href: "/runs", label: "Runs", icon: IconRuns },
    ],
  },
  {
    title: "System",
    items: [
      { href: "/overview", label: "Overview", icon: IconOverview },
      { href: "/settings", label: "Settings", icon: IconSettings },
    ],
  },
];

export function Sidebar({ pathname, activePartition }: { pathname: string; activePartition: string | null }) {
  return (
    <aside className="app-sidebar">
      <div className="app-sidebar-brand">
        <span className="app-sidebar-brand-mark" aria-hidden="true" />
        <strong>Knowbase</strong>
      </div>
      <nav className="app-sidebar-nav" aria-label="Primary">
        {navGroups.map((group) => (
          <section key={group.title} className="app-sidebar-nav-group">
            <header className="app-sidebar-nav-group-title">{group.title}</header>
            <div className="app-sidebar-nav-group-items">
              {group.items.map((item) => {
                const href = withBasePath(item.href);
                const active = pathname === item.href || (item.href === "/overview" && pathname === "/");
                const Icon = item.icon;
                return (
                  <a key={item.href} className={active ? "is-active" : ""} href={href}>
                    <Icon className="app-sidebar-nav-icon" />
                    <span>{item.label}</span>
                  </a>
                );
              })}
            </div>
          </section>
        ))}
      </nav>
      <div className="app-sidebar-footer">
        <div className="app-sidebar-active-partition">
          <span>Active partition</span>
          <strong>{activePartition || "No active partition"}</strong>
        </div>
      </div>
    </aside>
  );
}
