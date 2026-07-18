import { useEffect, useMemo } from "react";

import MonacoEditor from "@monaco-editor/react";
import MDEditor from "@uiw/react-md-editor";

export type IngestContentFormat = "text" | "markdown" | "json";

type DocumentContentEditorProps = {
  value: string;
  format: IngestContentFormat;
  disabled?: boolean;
  onFormatChange: (format: IngestContentFormat) => void;
  onValueChange: (value: string) => void;
  onJsonErrorChange?: (message: string) => void;
};

function getMonacoLanguage(format: IngestContentFormat) {
  if (format === "json") {
    return "json";
  }
  return "plaintext";
}

function getPlaceholder(format: IngestContentFormat) {
  if (format === "json") {
    return '{\n  "title": "Example",\n  "content": "..." \n}';
  }
  if (format === "markdown") {
    return "# Title\n\n- key point\n- another point";
  }
  return "Paste one document or case content here...";
}

export function DocumentContentEditor({
  value,
  format,
  disabled = false,
  onFormatChange,
  onValueChange,
  onJsonErrorChange,
}: DocumentContentEditorProps) {
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
      <div className="ingest-content-head">
        <span>Document content</span>
        <div className="ingest-content-tools">
          <select
            className="ingest-format-select"
            value={format}
            onChange={(event) => onFormatChange(event.target.value as IngestContentFormat)}
            disabled={disabled}
          >
            <option value="text">Plain text</option>
            <option value="markdown">Markdown</option>
            <option value="json">JSON</option>
          </select>
        </div>
      </div>

      {format === "markdown" ? (
        <div className="ingest-markdown-editor-shell">
          <MDEditor
            value={value}
            onChange={(next) => onValueChange(next ?? "")}
            preview="live"
            height="100%"
            visibleDragbar={false}
            extraCommands={[]}
            textareaProps={{
              placeholder: getPlaceholder(format),
              disabled,
            }}
          />
        </div>
      ) : (
        <div className={`ingest-content-frame is-${format}${format === "text" ? " is-single" : ""}`}>
          <div className="ingest-monaco-shell">
            <MonacoEditor
              height="100%"
              language={getMonacoLanguage(format)}
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
              path={`knowbase-ingest.${format === "json" ? "json" : "txt"}`}
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
