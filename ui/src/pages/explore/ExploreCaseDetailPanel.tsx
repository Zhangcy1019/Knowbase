import { useEffect, useState } from "react";

import type { KnowbaseCaseDocument } from "../../shared/api";
import { SourceContentEditor, detectSourceContentFormat, type SourceContentFormat } from "../../shared/component/source_content";
import { IconTraceDetail } from "../../shared/icons";
import { SourceContentViewer } from "../../shared/component/source_content";
import { formatDateTime, getProfileEntries, inferStatus, PanelMark } from "./explore_shared";

type ExploreCaseDetailPanelProps = {
  selectedCase: KnowbaseCaseDocument | null;
  loadingDetail: boolean;
  savingCase: boolean;
  detailErrorMessage: string;
  onSaveCase: (payload: { title: string; sourceContent: string }) => void;
};

export function ExploreCaseDetailPanel({
  selectedCase,
  loadingDetail,
  savingCase,
  detailErrorMessage,
  onSaveCase,
}: ExploreCaseDetailPanelProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draftSourceContent, setDraftSourceContent] = useState("");
  const [draftFormat, setDraftFormat] = useState<SourceContentFormat>("text");
  const [jsonError, setJsonError] = useState("");

  useEffect(() => {
    if (!selectedCase) {
      setIsEditing(false);
      setDraftSourceContent("");
      setDraftFormat("text");
      setJsonError("");
      return;
    }
    setIsEditing(false);
    setDraftSourceContent(selectedCase.source_content || "");
    setDraftFormat(detectSourceContentFormat(selectedCase.source_content || ""));
    setJsonError("");
  }, [selectedCase]);

  const selectedStatus = selectedCase ? inferStatus(selectedCase) : "stable";
  const selectedFacetEntries = selectedCase ? getProfileEntries(selectedCase.facets) : [];
  const selectedSemanticEntries = selectedCase ? getProfileEntries(selectedCase.semantic_profile) : [];
  const canSave = Boolean(draftSourceContent.trim()) && !jsonError && !savingCase;

  return (
    <article className="skeleton-card explore-detail-card">
      <div className="explore-panel-head">
        <div className="explore-panel-heading">
          <PanelMark>
            <IconTraceDetail />
          </PanelMark>
          <h3>Case Detail</h3>
        </div>
      </div>
      <div className="explore-detail-scroll">
        {!selectedCase && !loadingDetail ? (
          <div className="explore-empty-state">
            <strong>Select a case</strong>
          </div>
        ) : null}
        {loadingDetail ? (
          <div className="explore-empty-state">
            <strong>Loading...</strong>
          </div>
        ) : null}
        {selectedCase ? (
          <>
            <div className="explore-detail-meta">
              <span className={`explore-inline-status is-${selectedStatus}`}>{selectedStatus}</span>
              <code>{selectedCase.case_id}</code>
            </div>
            <h4>{selectedCase.title || selectedCase.case_id}</h4>
            <dl className="explore-detail-grid">
              <div>
                <dt>Partition</dt>
                <dd>{selectedCase.partition}</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>{selectedCase.metadata?.status || "--"}</dd>
              </div>
              <div>
                <dt>Source</dt>
                <dd>{selectedCase.metadata?.source || "--"}</dd>
              </div>
              <div>
                <dt>Updated</dt>
                <dd>{formatDateTime(selectedCase.updated_at)}</dd>
              </div>
              <div>
                <dt>Created</dt>
                <dd>{formatDateTime(selectedCase.created_at)}</dd>
              </div>
            </dl>
            {detailErrorMessage ? (
              <div className="explore-detail-error">
                <strong>{detailErrorMessage}</strong>
              </div>
            ) : null}
            <section className="explore-detail-section">
              <div className="explore-detail-section-head">
                <h5>Summary</h5>
              </div>
              {selectedCase.summary_text ? (
                <div className="explore-detail-summary">{selectedCase.summary_text}</div>
              ) : (
                <div className="explore-detail-empty">No summary.</div>
              )}
            </section>
            <section className="explore-detail-section">
              <div className="explore-detail-section-head">
                <h5>Semantic Profile</h5>
              </div>
              {selectedSemanticEntries.length === 0 ? (
                <div className="explore-detail-empty">No semantic profile.</div>
              ) : (
                <div className="explore-kv-list">
                  {selectedSemanticEntries.map(([key, values]) => (
                    <div key={key} className="explore-kv-item">
                      <strong>{key}</strong>
                      <div className="explore-kv-values">
                        {values.length === 0 ? <span className="is-empty">--</span> : null}
                        {values.map((value) => (
                          <span key={`${key}-${value}`}>{value}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="explore-detail-section">
              <div className="explore-detail-section-head">
                <h5>Facet Profile</h5>
              </div>
              {selectedFacetEntries.length === 0 ? (
                <div className="explore-detail-empty">No facet values.</div>
              ) : (
                <div className="explore-kv-list">
                  {selectedFacetEntries.map(([key, values]) => (
                    <div key={key} className="explore-kv-item">
                      <strong>{key}</strong>
                      <div className="explore-kv-values">
                        {values.length === 0 ? <span className="is-empty">--</span> : null}
                        {values.map((value) => (
                          <span key={`${key}-${value}`}>{value}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="explore-detail-section">
              <div className="explore-detail-section-head">
                <h5>Source Refs</h5>
              </div>
              {selectedCase.source_refs?.length ? (
                <div className="explore-ref-list">
                  {selectedCase.source_refs.map((refValue) => (
                    <code key={refValue}>{refValue}</code>
                  ))}
                </div>
              ) : (
                <div className="explore-detail-empty">No source refs.</div>
              )}
            </section>

            {isEditing ? (
              <section className="explore-detail-section">
                <div className="explore-detail-section-head">
                  <div className="explore-detail-section-titleline">
                    <h5>Source Content</h5>
                    <select
                      className="explore-detail-format-select"
                      value={draftFormat}
                      onChange={(event) => setDraftFormat(event.target.value as SourceContentFormat)}
                      disabled={savingCase}
                    >
                      <option value="text">Plain text</option>
                      <option value="markdown">Markdown</option>
                      <option value="json">JSON</option>
                    </select>
                  </div>
                  <div className="explore-detail-actions">
                    <button
                      type="button"
                      className="explore-detail-action is-secondary"
                      onClick={() => {
                        setIsEditing(false);
                        setDraftSourceContent(selectedCase.source_content || "");
                        setDraftFormat(detectSourceContentFormat(selectedCase.source_content || ""));
                        setJsonError("");
                      }}
                      disabled={savingCase}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      className="explore-detail-action is-primary"
                      onClick={() =>
                        onSaveCase({
                          title: selectedCase.title || "",
                          sourceContent: draftSourceContent,
                        })
                      }
                      disabled={!canSave}
                    >
                      {savingCase ? "Saving..." : "Save"}
                    </button>
                  </div>
                </div>
                <div className="explore-detail-editor-shell">
                  <SourceContentEditor
                    value={draftSourceContent}
                    format={draftFormat}
                    disabled={savingCase}
                    title=""
                    markdownMode="custom-live"
                    showFormatSelector={false}
                    onFormatChange={setDraftFormat}
                    onValueChange={setDraftSourceContent}
                    onJsonErrorChange={setJsonError}
                  />
                </div>
              </section>
            ) : (
              <section className="explore-detail-section">
                <div className="explore-detail-section-head">
                  <div className="explore-detail-section-titleline">
                    <h5>Source Content</h5>
                    <span className="explore-detail-format">
                      {draftFormat === "markdown"
                        ? "Markdown"
                        : draftFormat === "json"
                          ? "JSON"
                          : "Plain text"}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="explore-detail-action is-secondary"
                    onClick={() => setIsEditing(true)}
                  >
                    Edit
                  </button>
                </div>
                <SourceContentViewer
                  value={selectedCase.source_content || ""}
                  title=""
                  showSection={false}
                />
              </section>
            )}
          </>
        ) : null}
      </div>
    </article>
  );
}
