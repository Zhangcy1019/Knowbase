type AnyRecord = Record<string, unknown>;

function asRecord(value: unknown): AnyRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? value as AnyRecord : {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function hasValue(value: unknown) {
  return Array.isArray(value) ? value.length > 0 : Boolean(value);
}

/** Derive the useful result state when older audit records only say completed. */
export function effectiveStageStatus(title: string, value: unknown, fallback = "not run") {
  const stage = asRecord(asRecord(value).stage || value);
  if (!Object.keys(stage).length) return fallback;
  const explicit = String(stage.status || "");
  if (["blocked", "failed", "not_run"].includes(explicit)) return explicit;
  const output = asRecord(stage.output || stage);

  if (title === "Preparation") {
    const consistency = String(output.consistency_status || "");
    if (["inconsistent", "stale"].includes(consistency)) return "blocked";
    return output.coverage ? "passed" : "no_action";
  }
  if (title === "Proposal") {
    const proposal = asRecord(output.proposal);
    if (output.status === "blocked") return "blocked";
    return asArray(proposal.suggested_new_keys).length
      || asArray(proposal.suggested_updated_keys).length
      || asArray(proposal.suggested_removed_keys).length
      ? "completed"
      : "no_action";
  }
  if (title === "Projection") {
    const changes = asArray(output.changes);
    const targets = asArray(output.target_case_ids);
    return changes.length ? "completed" : targets.length ? "passed" : "no_action";
  }
  if (title === "Mutation Plan") {
    return asArray(output.case_changes).length || hasValue(output.accepted_schema) ? "completed" : "no_action";
  }
  if (title === "Apply") {
    const changed = asArray(output.updated_case_ids).length
      || asArray(output.updated_paths).length
      || asArray(output.commit_paths).length;
    return changed ? "completed" : "passed";
  }
  return explicit || fallback;
}
