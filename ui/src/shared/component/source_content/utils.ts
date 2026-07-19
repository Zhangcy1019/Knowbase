import type { SourceContentFormat } from "./types";

export function detectSourceContentFormat(value: string): SourceContentFormat {
  const normalized = value.trim();
  if (!normalized) {
    return "text";
  }

  try {
    const parsed = JSON.parse(normalized);
    if (parsed && typeof parsed === "object") {
      return "json";
    }
  } catch {
    // fall through
  }

  const markdownSignals = [
    /^#{1,6}\s/m,
    /^\s*[-*+]\s/m,
    /^\s*\d+\.\s/m,
    /\[[^\]]+\]\([^)]+\)/m,
    /```[\s\S]*```/m,
    /^\s*>\s/m,
  ];

  if (markdownSignals.some((pattern) => pattern.test(normalized))) {
    return "markdown";
  }
  return "text";
}

export function formatSourceContentLabel(format: SourceContentFormat) {
  if (format === "json") {
    return "JSON";
  }
  if (format === "markdown") {
    return "Markdown";
  }
  return "Text";
}

export function getSourceContentPlaceholder(format: SourceContentFormat) {
  if (format === "json") {
    return '{\n  "title": "Example",\n  "content": "..." \n}';
  }
  if (format === "markdown") {
    return "# Title\n\n- key point\n- another point";
  }
  return "Paste one document or case content here...";
}

export function getSourceContentMonacoLanguage(format: SourceContentFormat) {
  if (format === "json") {
    return "json";
  }
  return "plaintext";
}
