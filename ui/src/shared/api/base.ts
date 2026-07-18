export async function requestJson<T>(path: string, init?: RequestInit) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
    ...init,
  });
  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: unknown; message?: unknown };
      const detail =
        typeof payload.detail === "string"
          ? payload.detail
          : typeof payload.message === "string"
            ? payload.message
            : "";
      if (detail) {
        message = detail;
      }
    } catch {
      try {
        const text = (await response.text()).trim();
        if (text) {
          message = text;
        }
      } catch {
        // Ignore unreadable error bodies and keep the status-based message.
      }
    }
    throw new Error(message);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
