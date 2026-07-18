import type { ChangeEvent, ReactNode } from "react";
import { useMemo, useState } from "react";

import "./ingest.css";
import { DocumentContentEditor, type IngestContentFormat } from "./DocumentContentEditor";
import { IconIngest, IconSend, IconTraceDetail } from "../../shared/icons";
import { createKnowbaseCase, type IngestResponse } from "../../shared/api";

type IngestFormState = {
  title: string;
  sourceRefs: string;
  sourceContent: string;
  contentFormat: IngestContentFormat;
};

const defaultFormState: IngestFormState = {
  title: "",
  sourceRefs: "",
  sourceContent: "",
  contentFormat: "text",
};

function PanelMark({ children }: { children: ReactNode }) {
  return <span className="ingest-panel-mark">{children}</span>;
}

function buildResultLines(result: IngestResponse | null, activePartition: string | null) {
  return [
    { label: "Status", value: result?.detail.processing_status || "Idle" },
    { label: "Partition", value: result?.partition || activePartition || "--" },
    { label: "Case ID", value: result?.created_id || "Pending" },
    {
      label: "Backlog",
      value: result?.detail.backlog_event_id || "Not created",
    },
  ];
}

function parseSourceRefs(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

export function IngestPage({ activePartition }: { activePartition: string | null }) {
  const [form, setForm] = useState<IngestFormState>(defaultFormState);
  const [result, setResult] = useState<IngestResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [jsonError, setJsonError] = useState("");
  const titleValid = form.title.trim().length > 0;
  const contentValid = form.sourceContent.trim().length > 0;
  const submitDisabled = !activePartition || submitting || !titleValid || !contentValid;
  const resultLines = useMemo(() => buildResultLines(result, activePartition), [result, activePartition]);
  const payloadPreview = useMemo(
    () => ({
      partition: activePartition || "",
      title: form.title,
      source_content: form.sourceContent,
      source_refs: parseSourceRefs(form.sourceRefs),
      content_format: form.contentFormat,
    }),
    [activePartition, form],
  );

  function updateField<K extends keyof IngestFormState>(key: K) {
    return (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setForm((current) => ({ ...current, [key]: event.target.value }));
    };
  }

  function handleClear() {
    setForm((current) => ({
      ...defaultFormState,
      contentFormat: current.contentFormat,
    }));
    setResult(null);
    setErrorMessage("");
    setJsonError("");
  }

  async function handleSubmit() {
    if (!activePartition?.trim()) {
      setErrorMessage("Select or create a partition first.");
      return;
    }
    if (!titleValid) {
      setErrorMessage("Title is required.");
      return;
    }
    if (!contentValid) {
      setErrorMessage("Document content is required.");
      return;
    }
    if (jsonError) {
      setErrorMessage(`JSON parse error: ${jsonError}`);
      return;
    }
    setSubmitting(true);
    setErrorMessage("");
    try {
      const response = await createKnowbaseCase({
        partition: activePartition,
        title: form.title,
        source_content: form.sourceContent,
        source_refs: parseSourceRefs(form.sourceRefs),
      });
      setResult(response);
    } catch (error: unknown) {
      setResult(null);
      setErrorMessage(error instanceof Error ? error.message : "Failed to submit ingest request.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="ingest-page">
      <header className="ingest-page-header">
        <div className="ingest-page-copy">
          <h2>Ingest</h2>
        </div>
      </header>

      <section className="ingest-workspace">
        <article className="skeleton-card ingest-editor-card">
          <div className="ingest-panel-head">
            <div className="ingest-panel-heading">
              <PanelMark>
                <IconIngest />
              </PanelMark>
              <h3>Input</h3>
            </div>
          </div>

          <div className="ingest-form-grid">
            <label className="ingest-field">
              <span>Partition</span>
              <input type="text" value={activePartition || ""} readOnly placeholder="No active partition" />
            </label>

            <label className="ingest-field">
              <span>Title</span>
              <input type="text" placeholder="Document title" value={form.title} onChange={updateField("title")} />
            </label>

            <label className="ingest-field is-wide">
              <span>Source refs</span>
              <input
                type="text"
                placeholder="url, file path, external ref..."
                value={form.sourceRefs}
                onChange={updateField("sourceRefs")}
              />
            </label>

            <DocumentContentEditor
              value={form.sourceContent}
              format={form.contentFormat}
              disabled={submitting}
              onFormatChange={(contentFormat) => setForm((current) => ({ ...current, contentFormat }))}
              onValueChange={(sourceContent) => setForm((current) => ({ ...current, sourceContent }))}
              onJsonErrorChange={setJsonError}
            />
          </div>

          <div className="ingest-actions-bar">
            <div className="ingest-actions">
              <button type="button" className="ingest-secondary-button" onClick={handleClear}>
                Clear
              </button>
              <button
                type="button"
                className="ingest-primary-button"
                onClick={() => void handleSubmit()}
                disabled={submitDisabled}
              >
                {submitting ? "Submitting..." : "Submit"}
              </button>
            </div>
          </div>
        </article>

        <div className={`ingest-side-stack${!result && !errorMessage ? " is-empty" : ""}`}>
          {!result && !errorMessage ? (
            <article className="skeleton-card ingest-empty-card">
              <div className="ingest-empty-state">
                <PanelMark>
                  <IconTraceDetail />
                </PanelMark>
                <strong>No submission yet</strong>
              </div>
            </article>
          ) : (
            <>
              <article className="skeleton-card ingest-result-card">
                <div className="ingest-panel-head">
                  <div className="ingest-panel-heading">
                    <PanelMark>
                      <IconTraceDetail />
                    </PanelMark>
                    <h3>Result</h3>
                  </div>
                </div>

                <div className="ingest-result-state">
                  <strong>
                    {errorMessage
                      ? "Submit failed"
                      : result?.detail.accepted
                        ? "Accepted"
                        : "Rejected"}
                  </strong>
                  {errorMessage ? <span className="ingest-result-note is-error">{errorMessage}</span> : null}
                </div>

                <div className="ingest-result-list">
                  {resultLines.map((item) => (
                    <div key={item.label} className="ingest-result-row">
                      <span>{item.label}</span>
                      <strong>{item.value}</strong>
                    </div>
                  ))}
                </div>
              </article>

              <article className="skeleton-card ingest-preview-card">
                <div className="ingest-panel-head">
                  <div className="ingest-panel-heading">
                    <PanelMark>
                      <IconSend />
                    </PanelMark>
                    <h3>Payload</h3>
                  </div>
                </div>

                <div className="ingest-result-log">
                  <pre>{JSON.stringify(result ?? payloadPreview, null, 2)}</pre>
                </div>
              </article>
            </>
          )}
        </div>
      </section>
    </section>
  );
}
