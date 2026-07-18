import { useEffect, useState } from "react";
import { stripBasePath } from "./basePath";
import { AppShell } from "./shell/AppShell";
import { AppRouter, resolvePath } from "./router";
import "../pages/shared/page.css";

export function App() {
  const [pathname, setPathname] = useState(resolvePath(stripBasePath(window.location.pathname)));
  const [activePartition, setActivePartition] = useState<string | null>(null);

  useEffect(() => {
    function onPopState() {
      setPathname(resolvePath(stripBasePath(window.location.pathname)));
    }

    function onDocumentClick(event: MouseEvent) {
      const target = event.target as HTMLElement | null;
      const anchor = target?.closest("a");
      if (!anchor || anchor.target || anchor.hasAttribute("download")) {
        return;
      }
      const url = new URL(anchor.href);
      if (url.origin !== window.location.origin) {
        return;
      }
      event.preventDefault();
      window.history.pushState({}, "", `${url.pathname}${url.search}${url.hash}`);
      setPathname(resolvePath(stripBasePath(window.location.pathname)));
    }

    window.addEventListener("popstate", onPopState);
    document.addEventListener("click", onDocumentClick);
    return () => {
      window.removeEventListener("popstate", onPopState);
      document.removeEventListener("click", onDocumentClick);
    };
  }, []);

  return (
    <AppShell pathname={pathname} activePartition={activePartition}>
      <AppRouter
        pathname={pathname}
        activePartition={activePartition}
        onActivatePartition={setActivePartition}
      />
    </AppShell>
  );
}
