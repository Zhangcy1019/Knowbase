"""Dispatch backlog batches into runtime requests."""

from __future__ import annotations

from internal.backlog.planning import BacklogPreparationPlanner, BatchWorkingSetBuilder
from internal.models import BacklogBatch
from internal.runtime.contracts import RuntimeRunRequest


class KnowbaseBacklogDispatchService:
    """Translate one assembled backlog batch into one runtime request."""

    def __init__(
        self,
        *,
        working_set_builder: BatchWorkingSetBuilder,
        preparation_planner: BacklogPreparationPlanner,
    ):
        self._working_set_builder = working_set_builder
        self._preparation_planner = preparation_planner

    def build_runtime_request(self, *, batch: BacklogBatch) -> RuntimeRunRequest:
        working_set = self._working_set_builder.build(batch=batch)
        preparation = self._preparation_planner.build_preparation(batch_working_set=working_set)
        action_hints = self._build_action_hints(preparation=preparation)
        return RuntimeRunRequest(
            request_id=batch.batch_id,
            source_type="backlog",
            source_ref=batch.batch_id,
            partition=batch.partition,
            objective=f"Process backlog batch {batch.batch_id} for partition {batch.partition or 'global'}",
            prompt=preparation.summary,
            context={
                "batch_id": batch.batch_id,
                "batch_summary": batch.summary,
                "batch_event_ids": batch.event_ids,
                "batch_event_type_counts": batch.event_type_counts,
                "batch_resource_refs": batch.resource_refs,
                "trigger_source": batch.trigger_source,
                "batch_working_set": working_set.model_dump(mode="json"),
                "batch_preparation": preparation.model_dump(mode="json"),
            },
            allowed_skills=sorted(
                {
                    hint["skill_id"]
                    for hint in action_hints
                    if hint.get("kind") == "skill_call" and str(hint.get("skill_id") or "").strip()
                }
            ),
            allowed_tools=[],
            max_steps=max(16, len(action_hints) * 3 or 16),
            max_tool_calls=24,
            max_skill_calls=max(8, len(action_hints) or 8),
            risk_level=preparation.risk_level,
            requires_review=preparation.requires_review,
            metadata={"actions": action_hints},
        )

    @staticmethod
    def _build_action_hints(*, preparation) -> list[dict[str, object]]:
        actions: list[dict[str, object]] = []
        for candidate in preparation.candidates:
            if candidate.action_type == "refresh_selected_case_representation":
                actions.append(
                    {
                        "kind": "skill_call",
                        "action_id": f"{candidate.candidate_id}:action",
                        "title": "case.rebuild_case",
                        "summary": candidate.reason,
                        "skill_id": "case.rebuild_case",
                        "inputs": {"case_id": candidate.target_id, "force": True},
                        "metadata": candidate.metadata,
                        "risk_level": candidate.risk_level,
                        "requires_review": candidate.requires_review,
                    }
                )
                continue
            if candidate.action_type == "refresh_selected_case_facets":
                actions.append(
                    {
                        "kind": "skill_call",
                        "action_id": f"{candidate.candidate_id}:action",
                        "title": "case.refresh_case_facets",
                        "summary": candidate.reason,
                        "skill_id": "case.refresh_case_facets",
                        "inputs": {"case_id": candidate.target_id, "force": True},
                        "metadata": candidate.metadata,
                        "risk_level": candidate.risk_level,
                        "requires_review": candidate.requires_review,
                    }
                )
        return actions
