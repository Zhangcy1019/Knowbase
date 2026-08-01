import type { ReactNode } from "react";

type KnowledgeRecordTreeProps = {
  value: unknown;
};

type AnyRecord = Record<string, unknown>;

function fieldLabel(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function RecordValue({ value }: { value: unknown }) {
  if (value === null || value === undefined || value === "") {
    return <span className="knowledge-record-empty">Not recorded</span>;
  }
  if (typeof value !== "object") {
    return <span className="knowledge-record-text">{String(value)}</span>;
  }
  if (Array.isArray(value)) {
    if (!value.length) return <span className="knowledge-record-empty">Empty list</span>;
    return (
      <div className="knowledge-record-list">
        {value.map((item, index) => (
          <div className="knowledge-record-list-item" key={index}>
            <span className="knowledge-record-index">{index + 1}</span>
            <RecordValue value={item} />
          </div>
        ))}
      </div>
    );
  }
  const entries = Object.entries(value as AnyRecord);
  if (!entries.length) return <span className="knowledge-record-empty">Empty object</span>;
  return (
    <div className="knowledge-record-object">
      {entries.map(([key, item]) => (
        <div className="knowledge-record-field" key={key}>
          <span className="knowledge-record-label">{fieldLabel(key)}</span>
          <RecordValue value={item} />
        </div>
      ))}
    </div>
  );
}

export function KnowledgeRecordTree({ value }: KnowledgeRecordTreeProps) {
  return <div className="knowledge-record-tree"><RecordValue value={value} /></div>;
}
