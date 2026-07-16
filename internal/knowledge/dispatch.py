"""Knowledge-owned task shaping between backlog batches and runtime runs."""

from __future__ import annotations

from internal.knowledge.planning import BacklogPreparationPlanner, BatchWorkingSetBuilder
from internal.models import BacklogBatch, KnowledgeTask, KnowledgeTaskActionHint
from internal.runtime.contracts import RuntimeRunRequest


class KnowledgeTaskBuilder:
    """Build one knowledge task from one backlog batch."""

    def __init__(
        self,
        *,
        working_set_builder: BatchWorkingSetBuilder,
        preparation_planner: BacklogPreparationPlanner,
    ):
        self._working_set_builder = working_set_builder
        self._preparation_planner = preparation_planner

    def build_task(self, *, batch: BacklogBatch) -> KnowledgeTask:
        working_set = self._working_set_builder.build(batch=batch)
        preparation = self._preparation_planner.build_preparation(batch_working_set=working_set)
        action_hints = self._build_action_hints(preparation=preparation)
        return KnowledgeTask(
            task_id=batch.batch_id,
            source_batch_id=batch.batch_id,
            source_type="backlog",
            partition=batch.partition,
            domain="backlog_maintenance",
            objective=f"Process backlog batch {batch.batch_id} for partition {batch.partition or 'global'}",
            prompt=preparation.summary,
            task_payload={
                "batch_id": batch.batch_id,
                "batch_summary": batch.summary,
                "batch_event_ids": batch.event_ids,
                "batch_event_type_counts": batch.event_type_counts,
                "batch_resource_refs": batch.resource_refs,
                "trigger_source": batch.trigger_source,
                "batch_working_set": working_set.model_dump(mode="json"),
                "batch_preparation": preparation.model_dump(mode="json"),
            },
            action_hints=action_hints,
            allowed_skills=sorted(
                {
                    hint.skill_id
                    for hint in action_hints
                    if hint.kind == "skill_call" and hint.skill_id.strip()
                }
            ),
            allowed_tools=sorted(
                {
                    hint.tool_id
                    for hint in action_hints
                    if hint.kind == "tool_call" and hint.tool_id.strip()
                }
            ),
            max_steps=max(16, len(action_hints) * 3 or 16),
            max_tool_calls=24,
            max_skill_calls=max(8, len(action_hints) or 8),
            risk_level=preparation.risk_level,
            requires_review=preparation.requires_review,
            metadata={
                "preparation_notes": list(preparation.notes),
                "knowledge_domain": "backlog_maintenance",
            },
        )

    @staticmethod
    def _build_action_hints(*, preparation) -> list[KnowledgeTaskActionHint]:
        actions: list[KnowledgeTaskActionHint] = []
        for candidate in preparation.candidates:
            if candidate.action_type == "refresh_selected_case_representation":
                actions.append(
                    KnowledgeTaskActionHint(
                        kind="skill_call",
                        action_id=f"{candidate.candidate_id}:action",
                        title="case.rebuild_case",
                        summary=candidate.reason,
                        skill_id="case.rebuild_case",
                        inputs={"case_id": candidate.target_id, "force": True},
                        metadata=candidate.metadata,
                        risk_level=candidate.risk_level,
                        requires_review=candidate.requires_review,
                    )
                )
                continue
            if candidate.action_type == "refresh_selected_case_facets":
                actions.append(
                    KnowledgeTaskActionHint(
                        kind="skill_call",
                        action_id=f"{candidate.candidate_id}:action",
                        title="case.refresh_case_facets",
                        summary=candidate.reason,
                        skill_id="case.refresh_case_facets",
                        inputs={"case_id": candidate.target_id, "force": True},
                        metadata=candidate.metadata,
                        risk_level=candidate.risk_level,
                        requires_review=candidate.requires_review,
                    )
                )
        return actions


class RuntimeRequestBuilder:
    """Translate one knowledge task into one runtime request."""

    def build_request(self, *, task: KnowledgeTask) -> RuntimeRunRequest:
        return RuntimeRunRequest(
            request_id=task.task_id,
            source_type=task.source_type,
            source_ref=task.source_batch_id,
            partition=task.partition,
            objective=task.objective,
            prompt=task.prompt,
            task_payload=dict(task.task_payload),
            task_hints=[item.model_dump(mode="json") for item in task.action_hints],
            allowed_skills=list(task.allowed_skills),
            allowed_tools=list(task.allowed_tools),
            max_steps=task.max_steps,
            max_tool_calls=task.max_tool_calls,
            max_skill_calls=task.max_skill_calls,
            risk_level=task.risk_level,
            requires_review=task.requires_review,
            metadata={
                "knowledge_domain": task.domain,
                "knowledge_task": task.model_dump(mode="json"),
                **dict(task.metadata),
            },
        )


class KnowbaseKnowledgeDispatchService:
    """Own the task-shaping step between backlog batches and runtime runs."""

    def __init__(
        self,
        *,
        task_builder: KnowledgeTaskBuilder,
        runtime_request_builder: RuntimeRequestBuilder | None = None,
    ):
        self._task_builder = task_builder
        self._runtime_request_builder = runtime_request_builder or RuntimeRequestBuilder()

    def build_task(self, *, batch: BacklogBatch) -> KnowledgeTask:
        return self._task_builder.build_task(batch=batch)

    def build_runtime_request(self, *, batch: BacklogBatch) -> RuntimeRunRequest:
        task = self.build_task(batch=batch)
        return self._runtime_request_builder.build_request(task=task)


__all__ = [
    "KnowledgeTaskBuilder",
    "RuntimeRequestBuilder",
    "KnowbaseKnowledgeDispatchService",
]
