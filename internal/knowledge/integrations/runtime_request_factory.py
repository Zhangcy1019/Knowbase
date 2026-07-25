"""Build runtime requests from Knowledge work commands."""

from __future__ import annotations

from internal.backlog.models import BacklogBatch
from internal.runtime.contracts import RuntimeRunRequest, RuntimeWorkProfile
from internal.runtime.verification.profile import RuntimeVerificationProfile

from internal.knowledge.batch.context_builder import BatchContextBuilder
from internal.knowledge.batch.working_set_builder import BatchWorkingSetBuilder


class RuntimeRequestFactory:
    """Translate Knowledge work commands into RuntimeRunRequest objects."""

    def __init__(
        self,
        *,
        working_set_builder: BatchWorkingSetBuilder,
        context_builder: BatchContextBuilder,
    ):
        self._working_set_builder = working_set_builder
        self._context_builder = context_builder

    def build_for_batch(self, *, batch: BacklogBatch, context=None, patch=None) -> RuntimeRunRequest:
        working_set = self._working_set_builder.build(batch=batch)
        preparation = self._context_builder.build_context(batch_working_set=working_set)
        instructions = [
            "Prefer evidence-backed knowledge maintenance decisions.",
            "Do not propose tool_call or skill_call actions outside the allowed capability lists.",
            "In analysis_only mode, summarize whether follow-up work is needed and stop when no executable action exists.",
            "Treat partition-level schema changes as high-signal decisions that require stable support across cases.",
            "Refresh case representation or facets only when the current runtime mode allows real execution.",
        ]
        acceptance = {
            "mode": "analysis_only",
            "completion_checks": [
                "produce a concise reasoning_summary",
                "produce a concise action_plan_summary",
                "do not propose non-executable actions",
            ],
            "review_triggers": [
                "insufficient evidence for safe follow-up recommendation",
                "conflicting maintenance signals across affected resources",
            ],
        }
        stop_policy = {
            "stop_when_no_executable_action": True,
            "stop_when_acceptance_satisfied": True,
        }
        risk_policy = {
            "risk_level": preparation.risk_level,
            "requires_review": preparation.requires_review,
        }
        return RuntimeRunRequest(
            request_id=batch.batch_id,
            source_type="backlog",
            source_ref=batch.batch_id,
            partition=batch.partition,
            work=RuntimeWorkProfile(
                objective=f"Process backlog batch {batch.batch_id} for partition {batch.partition or 'global'}",
                mission_summary=(
                    "Inspect the prepared backlog batch, determine whether knowledge maintenance follow-up is needed, "
                    "and summarize the next recommended work."
                ),
                instructions=instructions,
                input_context={
                    "batch_id": batch.batch_id,
                    "batch_summary": batch.summary,
                    "batch_event_ids": batch.event_ids,
                    "batch_event_type_counts": batch.event_type_counts,
                    "batch_resource_refs": batch.resource_refs,
                    "trigger_source": batch.trigger_source,
                    "batch_working_set": working_set.model_dump(mode="json"),
                    "batch_preparation": preparation.model_dump(mode="json"),
                },
                capability_hints=[],
                allowed_skills=[],
                allowed_tools=[],
                max_steps=8,
                max_tool_calls=0,
                max_skill_calls=0,
            ),
            objective=f"Process backlog batch {batch.batch_id} for partition {batch.partition or 'global'}",
            mission_summary=(
                "Inspect the prepared backlog batch, determine whether knowledge maintenance follow-up is needed, "
                "and summarize the next recommended work."
            ),
            instructions=instructions,
            input_context={
                "batch_id": batch.batch_id,
                "batch_summary": batch.summary,
                "batch_event_ids": batch.event_ids,
                "batch_event_type_counts": batch.event_type_counts,
                "batch_resource_refs": batch.resource_refs,
                "trigger_source": batch.trigger_source,
                "batch_working_set": working_set.model_dump(mode="json"),
                "batch_preparation": preparation.model_dump(mode="json"),
            },
            capability_hints=[],
            acceptance=acceptance,
            verification=RuntimeVerificationProfile(
                enabled=False,
                mode="deterministic",
                require_acceptance=True,
            ),
            stop_policy=stop_policy,
            risk_policy=risk_policy,
            allowed_skills=[],
            allowed_tools=[],
            max_steps=8,
            max_tool_calls=0,
            max_skill_calls=0,
            risk_level=preparation.risk_level,
            requires_review=preparation.requires_review,
            metadata={
                "runtime_mode": "analysis_only",
                "preparation_notes": list(preparation.notes),
                "knowledge_domain": "backlog_maintenance",
            },
        )
