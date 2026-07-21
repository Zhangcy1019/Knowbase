import type { ReactNode } from "react";

import type { KnowbaseCaseDocument } from "../../shared/api";

export function PanelMark({ children }: { children: ReactNode }) {
  return <span className="explore-panel-mark">{children}</span>;
}

export function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString([], {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function getProfileEntries(profile: Record<string, string[]> | undefined) {
  return Object.entries(profile ?? {}).filter(([key, values]) => key.trim() && Array.isArray(values));
}

export function inferStatus(item: KnowbaseCaseDocument): "stable" | "review" | "elevated" {
  const status = item.metadata?.status || "";
  if (status === "archived") {
    return "review";
  }
  return "stable";
}
