import { withBasePath } from "../basePath";
import type { SVGProps } from "react";

const navItems = [
  { href: "/overview", label: "Overview", icon: OverviewIcon },
  { href: "/explore", label: "Explore", icon: CasesIcon },
  { href: "/partition", label: "Partition", icon: PartitionIcon },
  { href: "/query", label: "Query", icon: QueryIcon },
  { href: "/backlog", label: "Backlog", icon: BacklogIcon },
  { href: "/runs", label: "Runs", icon: RunsIcon },
  { href: "/settings", label: "Settings", icon: SettingsIcon },
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

function NavIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props} />
  );
}

function OverviewIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <NavIcon {...props}>
      <rect x="3" y="3" width="5" height="5" rx="1.2" />
      <rect x="12" y="3" width="5" height="5" rx="1.2" />
      <rect x="3" y="12" width="5" height="5" rx="1.2" />
      <rect x="12" y="12" width="5" height="5" rx="1.2" />
    </NavIcon>
  );
}

function CasesIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <NavIcon {...props}>
      <path d="M6 3.5h6l3 3v10A1.5 1.5 0 0 1 13.5 18h-7A1.5 1.5 0 0 1 5 16.5v-11A2 2 0 0 1 7 3.5Z" />
      <path d="M12 3.5v3h3" />
      <path d="M7.5 10h5" />
      <path d="M7.5 13h5" />
    </NavIcon>
  );
}

function BacklogIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <NavIcon {...props}>
      <path d="M4 6.5h12" />
      <path d="M4 10h12" />
      <path d="M4 13.5h8" />
      <path d="M14 13.5h2" />
      <path d="M5 4h10a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Z" />
    </NavIcon>
  );
}

function QueryIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <NavIcon {...props}>
      <path d="M4.5 5.5a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2H9l-3.5 3v-3H6.5a2 2 0 0 1-2-2v-5Z" />
      <path d="M7.4 8h5.2" />
      <path d="M7.4 10.5h3.6" />
    </NavIcon>
  );
}

function PartitionIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <NavIcon {...props}>
      <path d="M4.5 5.5h11" />
      <path d="M4.5 10h11" />
      <path d="M4.5 14.5h7.5" />
      <path d="M15.5 5.5v9" />
      <path d="M9.5 5.5v9" />
      <path d="M4.5 5.5v9" />
    </NavIcon>
  );
}

function RunsIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <NavIcon {...props}>
      <path d="M4 5v10" />
      <path d="M10 5v10" />
      <path d="M16 5v10" />
      <circle cx="4" cy="8" r="1.6" />
      <circle cx="10" cy="12" r="1.6" />
      <circle cx="16" cy="7" r="1.6" />
      <path d="M5.5 8h3" />
      <path d="M11.5 11.2h3" />
    </NavIcon>
  );
}

function SettingsIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <NavIcon {...props}>
      <circle cx="10" cy="10" r="2.3" />
      <path d="M10 3.5v1.7" />
      <path d="M10 14.8v1.7" />
      <path d="M3.5 10h1.7" />
      <path d="M14.8 10h1.7" />
      <path d="M5.4 5.4l1.2 1.2" />
      <path d="M13.4 13.4l1.2 1.2" />
      <path d="M14.6 5.4l-1.2 1.2" />
      <path d="M6.6 13.4l-1.2 1.2" />
    </NavIcon>
  );
}
