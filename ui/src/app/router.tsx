import { OverviewPage } from "../pages/overview/OverviewPage";
import { ExplorePage } from "../pages/explore/ExplorePage";
import { BacklogPage } from "../pages/backlog/BacklogPage";
import { RunsPage } from "../pages/runs/RunsPage";
import { SettingsPage } from "../pages/settings/SettingsPage";
import { DesignPage } from "../pages/design/DesignPage";
import { QueryPage } from "../pages/query/QueryPage";

export function resolvePath(pathname: string) {
  if (pathname === "/" || pathname === "") {
    return "/overview";
  }
  if (pathname === "/overview") {
    return "/overview";
  }
  if (pathname === "/explore" || pathname === "/cases") {
    return "/explore";
  }
  if (pathname === "/backlog") {
    return "/backlog";
  }
  if (pathname === "/runs") {
    return "/runs";
  }
  if (pathname === "/settings") {
    return "/settings";
  }
  if (pathname === "/design") {
    return "/design";
  }
  if (pathname === "/query") {
    return "/query";
  }
  return "/overview";
}

export function AppRouter({
  pathname,
  activePartition,
  onActivatePartition,
}: {
  pathname: string;
  activePartition: string;
  onActivatePartition: (partitionName: string) => void;
}) {
  switch (pathname) {
    case "/explore":
      return <ExplorePage />;
    case "/backlog":
      return <BacklogPage />;
    case "/runs":
      return <RunsPage />;
    case "/settings":
      return <SettingsPage />;
    case "/design":
      return <DesignPage />;
    case "/query":
      return <QueryPage />;
    case "/overview":
    default:
      return <OverviewPage activePartition={activePartition} onActivatePartition={onActivatePartition} />;
  }
}
