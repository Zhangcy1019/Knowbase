import { forwardRef } from "react";
import type { CSSProperties } from "react";

import "./confirm.css";

type ConfirmDeletePopoverProps = {
  title: string;
  description: string;
  errorMessage?: string;
  pending?: boolean;
  className?: string;
  style?: CSSProperties;
  onCancel: () => void;
  onConfirm: () => void;
};

export const ConfirmDeletePopover = forwardRef<HTMLDivElement, ConfirmDeletePopoverProps>(
  function ConfirmDeletePopover(
    {
      title,
      description,
      errorMessage = "",
      pending = false,
      className = "",
      style,
      onCancel,
      onConfirm,
    },
    ref,
  ) {
    return (
      <div ref={ref} className={`confirm-delete-popover${className ? ` ${className}` : ""}`} style={style}>
        <strong>{title}</strong>
        <p>{description}</p>
        {errorMessage ? <div className="confirm-delete-error">{errorMessage}</div> : null}
        <div className="confirm-delete-actions">
          <button type="button" className="overview-inline-button" onClick={onCancel} disabled={pending}>
            Cancel
          </button>
          <button type="button" className="overview-primary-button is-danger" onClick={onConfirm} disabled={pending}>
            {pending ? "Deleting..." : "Delete"}
          </button>
        </div>
      </div>
    );
  },
);
