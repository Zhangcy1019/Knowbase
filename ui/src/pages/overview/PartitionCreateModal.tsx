import { useState } from "react";

import { createPartition, type PartitionDocument } from "../../shared/api";

type PartitionCreateModalProps = {
  open: boolean;
  onClose: () => void;
  onCreated: (partition: PartitionDocument) => Promise<void> | void;
};

export function PartitionCreateModal({ open, onClose, onCreated }: PartitionCreateModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<PartitionDocument["status"]>("active");
  const [errorMessage, setErrorMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (!open) {
    return null;
  }

  function handleClose() {
    if (submitting) return;
    setName("");
    setDescription("");
    setStatus("active");
    setErrorMessage("");
    onClose();
  }

  async function handleSubmit() {
    const partitionName = name.trim();
    if (!partitionName) {
      setErrorMessage("Partition name is required.");
      return;
    }
    try {
      setSubmitting(true);
      setErrorMessage("");
      const created = await createPartition({
        partition_name: partitionName,
        scenario_description: description.trim(),
        status,
      });
      await onCreated(created);
      setName("");
      setDescription("");
      setStatus("active");
      setErrorMessage("");
      onClose();
    } catch (error: unknown) {
      setErrorMessage(error instanceof Error ? error.message : "Partition creation failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="overview-modal-backdrop" role="presentation" onClick={handleClose}>
      <section
        className="overview-modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="partition-create-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="overview-modal-head">
          <div>
            <span className="overview-modal-kicker">Partition Manager</span>
            <h3 id="partition-create-title">Create Partition</h3>
          </div>
          <button type="button" className="overview-modal-close" onClick={handleClose} disabled={submitting}>
            Close
          </button>
        </div>

        <div className="overview-manager-form">
          <label className="overview-create-field">
            <span>Name</span>
            <input
              autoFocus
              disabled={submitting}
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Claims"
            />
          </label>
          <label className="overview-create-field">
            <span>Description</span>
            <textarea
              rows={4}
              disabled={submitting}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Scope, domain, and curation intent."
            />
          </label>
          <label className="overview-create-field">
            <span>Status</span>
            <select
              disabled={submitting}
              value={status}
              onChange={(event) => setStatus(event.target.value as PartitionDocument["status"])}
            >
              <option value="active">active</option>
              <option value="disabled">disabled</option>
              <option value="archived">archived</option>
            </select>
          </label>
          {errorMessage ? <div className="overview-manager-error">{errorMessage}</div> : null}
          <div className="overview-manager-actions overview-manager-actions-bottom">
            <button type="button" className="overview-inline-button" onClick={handleClose} disabled={submitting}>
              Cancel
            </button>
            <button type="button" className="overview-primary-button" onClick={handleSubmit} disabled={submitting}>
              {submitting ? "Creating..." : "Create Partition"}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
