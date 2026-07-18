import { useEffect, useRef, useState } from "react";

type CreatePartitionCardProps = {
  open: boolean;
  onClose: () => void;
  onSubmit?: (payload: { partitionName: string; scenarioDescription: string }) => Promise<void> | void;
};

export function CreatePartitionCard({ open, onClose, onSubmit }: CreatePartitionCardProps) {
  const cardRef = useRef<HTMLDivElement | null>(null);
  const [partitionName, setPartitionName] = useState("");
  const [scenarioDescription, setScenarioDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (!open) {
      setPartitionName("");
      setScenarioDescription("");
      setSubmitting(false);
      setErrorMessage("");
    }
  }, [open]);

  useEffect(() => {
    if (!open) {
      return undefined;
    }
    const handlePointerDown = (event: MouseEvent) => {
      if (!cardRef.current) {
        return;
      }
      if (cardRef.current.contains(event.target as Node)) {
        return;
      }
      onClose();
    };
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  const handleSubmit = async () => {
    const nextPartitionName = partitionName.trim();
    if (!nextPartitionName) {
      setErrorMessage("Partition name is required.");
      return;
    }
    try {
      setSubmitting(true);
      setErrorMessage("");
      await onSubmit?.({
        partitionName: nextPartitionName,
        scenarioDescription: scenarioDescription.trim(),
      });
      onClose();
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to create partition.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="overview-create-layer" aria-hidden={!open}>
      <div ref={cardRef} className="overview-create-card" role="dialog" aria-modal="true" aria-label="Create partition">
        <div className="overview-create-head">
          <div>
            <h4>Create partition</h4>
            <p>Define a new workspace partition.</p>
          </div>
        </div>

        <div className="overview-create-form">
          <label className="overview-create-field">
            <span>Name</span>
            <input
              disabled={submitting}
              value={partitionName}
              onChange={(event) => setPartitionName(event.target.value)}
              placeholder="Claims"
            />
          </label>

          <label className="overview-create-field">
            <span>Description</span>
            <textarea
              rows={4}
              disabled={submitting}
              value={scenarioDescription}
              onChange={(event) => setScenarioDescription(event.target.value)}
              placeholder="Scope, domain, and curation intent."
            />
          </label>
        </div>

        {errorMessage ? <div className="overview-create-error">{errorMessage}</div> : null}

        <div className="overview-create-actions">
          <button type="button" className="overview-create-button is-ghost" onClick={onClose} disabled={submitting}>
            Cancel
          </button>
          <button type="button" className="overview-create-button" onClick={handleSubmit} disabled={submitting}>
            {submitting ? "Submitting..." : "Submit"}
          </button>
        </div>
      </div>
    </div>
  );
}
