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
} from "../../shared/icons";

const navItems = [
  { href: "/overview", label: "Overview", icon: IconOverview },
  { href: "/ingest", label: "Ingest", icon: IconIngest },
  { href: "/explore", label: "Explore", icon: IconExplore },
  { href: "/partition", label: "Partition", icon: IconPartition },
  { href: "/query", label: "Query", icon: IconQuery },
  { href: "/backlog", label: "Backlog", icon: IconBacklog },
  { href: "/runs", label: "Runs", icon: IconRuns },
  { href: "/settings", label: "Settings", icon: IconSettings },
];

export function Sidebar({ pathname, activePartition }: { pathname: string; activePartition: string }) {
  return (
    <aside className="app-sidebar">
      <div className="app-sidebar-brand">
        <span className="app-sidebar-brand-mark" aria-hidden="true" />
        <strong>Knowbase</strong>
      </div>
      <nav className="app-sidebar-nav" aria-label="Primary">
        {navItems.map((item) => {
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
      </nav>
      <div className="app-sidebar-footer">
        <div className="app-sidebar-active-partition">
          <span>Active partition</span>
          <strong>{activePartition || "None"}</strong>
        </div>
      </div>
    </aside>
  );
}
