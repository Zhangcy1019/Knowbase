import type { PropsWithChildren } from "react";
import { Sidebar } from "./Sidebar";
import "./shell.css";

export function AppShell({
  pathname,
  activePartition,
  children,
}: PropsWithChildren<{ pathname: string; activePartition: string }>) {
  return (
    <div className="app-shell">
      <Sidebar pathname={pathname} activePartition={activePartition} />
      <div className="app-shell-main is-topbar-hidden">
        <main className="app-shell-content">{children}</main>
      </div>
    </div>
  );
}
