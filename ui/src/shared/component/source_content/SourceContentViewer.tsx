import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { detectSourceContentFormat, formatSourceContentLabel } from "./utils";

type SourceContentViewerProps = {
  value: string;
  title?: string;
  showSection?: boolean;
};

function SourceContentPreview({ value }: { value: string }) {
  const format = detectSourceContentFormat(value);

  if (!value.trim()) {
    return <div className="explore-detail-empty">No source content.</div>;
  }

  if (format === "json") {
    try {
      return <pre className="explore-detail-content">{JSON.stringify(JSON.parse(value), null, 2)}</pre>;
    } catch {
      return <pre className="explore-detail-content">{value}</pre>;
    }
  }

  if (format === "markdown") {
    return (
      <div className="explore-detail-markdown" data-color-mode="light">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{value}</ReactMarkdown>
      </div>
    );
  }

  return <pre className="explore-detail-content">{value}</pre>;
}

export function SourceContentViewer({
  value,
  title = "Source Content",
  showSection = true,
}: SourceContentViewerProps) {
  const format = detectSourceContentFormat(value);
  const content = (
    <>
      {title ? (
        <div className="explore-detail-section-head">
          <h5>{title}</h5>
          <span className="explore-detail-format">{formatSourceContentLabel(format)}</span>
        </div>
      ) : null}
      <SourceContentPreview value={value} />
    </>
  );

  if (!showSection) {
    return content;
  }

  return <section className="explore-detail-section">{content}</section>;
}
