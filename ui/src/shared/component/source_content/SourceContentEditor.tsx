import { useEffect, useMemo } from "react";

import MonacoEditor from "@monaco-editor/react";
import MDEditor from "@uiw/react-md-editor";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { SourceContentFormat } from "./types";
import { getSourceContentMonacoLanguage, getSourceContentPlaceholder } from "./utils";

type SourceContentEditorProps = {
  value: string;
  format: SourceContentFormat;
  disabled?: boolean;
  title?: string;
  markdownMode?: "uiw-live" | "custom-live";
  showFormatSelector?: boolean;
  onFormatChange: (format: SourceContentFormat) => void;
  onValueChange: (value: string) => void;
  onJsonErrorChange?: (message: string) => void;
};

export function SourceContentEditor({
  value,
  format,
  disabled = false,
  title = "Document content",
  markdownMode = "uiw-live",
  showFormatSelector = true,
  onFormatChange,
  onValueChange,
  onJsonErrorChange,
}: SourceContentEditorProps) {
  const jsonError = useMemo(() => {
    if (format !== "json" || !value.trim()) {
      return "";
    }
    try {
      JSON.parse(value);
      return "";
    } catch (error: unknown) {
      return error instanceof Error ? error.message : "Invalid JSON";
    }
  }, [format, value]);

  useEffect(() => {
    onJsonErrorChange?.(jsonError);
  }, [jsonError, onJsonErrorChange]);

  return (
    <div className="ingest-field ingest-content-field is-wide is-fill" data-color-mode="light">
      {title || showFormatSelector ? (
        <div className={`ingest-content-head${title ? "" : " is-compact"}`}>
          {title ? <span>{title}</span> : <span />}
          {showFormatSelector ? (
            <div className="ingest-content-tools">
              <select
                className="ingest-format-select"
                value={format}
                onChange={(event) => onFormatChange(event.target.value as SourceContentFormat)}
                disabled={disabled}
              >
                <option value="text">Plain text</option>
                <option value="markdown">Markdown</option>
                <option value="json">JSON</option>
              </select>
            </div>
          ) : null}
        </div>
      ) : null}

      {format === "markdown" ? (
        markdownMode === "uiw-live" ? (
          <div className="ingest-markdown-editor-shell">
            <MDEditor
              value={value}
              onChange={(next) => onValueChange(next ?? "")}
              preview="live"
              height="100%"
              visibleDragbar={false}
              extraCommands={[]}
              textareaProps={{
                placeholder: getSourceContentPlaceholder(format),
                disabled,
              }}
            />
          </div>
        ) : (
          <div className="ingest-content-frame ingest-content-frame-markdown">
            <div className="ingest-markdown-plain-shell">
              <textarea
                className="ingest-markdown-plain-input"
                value={value}
                onChange={(event) => onValueChange(event.target.value)}
                placeholder={getSourceContentPlaceholder(format)}
                disabled={disabled}
              />
            </div>
            <div className="ingest-content-preview ingest-content-preview-markdown">
              {value.trim() ? (
                <div className="ingest-markdown-preview-body">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{value}</ReactMarkdown>
                </div>
              ) : (
                <div className="ingest-content-state">
                  <strong>Markdown preview</strong>
                  <span>Rendered content will appear here.</span>
                </div>
              )}
            </div>
          </div>
        )
      ) : (
        <div className={`ingest-content-frame is-${format}${format === "text" ? " is-single" : ""}`}>
          <div className="ingest-monaco-shell">
            <MonacoEditor
              height="100%"
              language={getSourceContentMonacoLanguage(format)}
              value={value}
              onChange={(next) => onValueChange(next ?? "")}
              options={{
                readOnly: disabled,
                minimap: { enabled: false },
                wordWrap: "on",
                lineNumbers: format === "json" ? "on" : "off",
                scrollBeyondLastLine: false,
                folding: format === "json",
                automaticLayout: true,
                fontSize: 13,
                tabSize: 2,
                padding: { top: 12, bottom: 12 },
              }}
              beforeMount={(monaco) => {
                monaco.editor.defineTheme("knowbase-light", {
                  base: "vs",
                  inherit: true,
                  rules: [],
                  colors: {
                    "editor.background": "#ffffff",
                    "editor.lineHighlightBackground": "#f6f9fc",
                  },
                });
              }}
              theme="knowbase-light"
              path={`knowbase-shared-source-content.${format === "json" ? "json" : "txt"}`}
              loading={<div className="ingest-content-state"><strong>Loading editor</strong></div>}
            />
          </div>

          {format === "json" ? (
            <div className="ingest-content-preview">
              {jsonError ? (
                <div className="ingest-content-state is-error">
                  <strong>JSON parse error</strong>
                  <span>{jsonError}</span>
                </div>
              ) : value.trim() ? (
                <pre>{JSON.stringify(JSON.parse(value), null, 2)}</pre>
              ) : (
                <div className="ingest-content-state">
                  <strong>JSON preview</strong>
                  <span>Valid JSON will be formatted here.</span>
                </div>
              )}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
