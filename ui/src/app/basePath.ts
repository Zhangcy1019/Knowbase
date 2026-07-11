const knownRoutes = ["/overview", "/cases", "/backlog", "/runs", "/settings", "/design", "/query", "/knowbase"];

export function getBasePath() {
  const pathname = window.location.pathname || "/";
  for (const route of knownRoutes) {
    if (pathname === route) {
      return "/";
    }
    if (pathname.endsWith(route)) {
      return pathname.slice(0, pathname.length - route.length) || "/";
    }
  }
  return "/";
}

export function withBasePath(path: string) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const basePath = getBasePath();
  if (basePath === "/") {
    return normalizedPath;
  }
  return `${basePath}${normalizedPath}`;
}

export function stripBasePath(pathname: string) {
  const basePath = getBasePath();
  if (basePath === "/") {
    return pathname || "/";
  }
  if (pathname === basePath) {
    return "/";
  }
  if (pathname.startsWith(basePath)) {
    return pathname.slice(basePath.length) || "/";
  }
  return pathname || "/";
}
