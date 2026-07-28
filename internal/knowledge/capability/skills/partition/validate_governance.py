"""Runtime skill for executing the complete governance validation pipeline."""

from __future__ import annotations

from datetime import datetime, timezone

from internal.knowledge.governance.validation import (
    GovernanceValidationContext,
    GovernanceValidationPipeline,
)
from internal.models.skill import SkillInvocation, SkillResult, SkillSpec
from internal.models.skill_context import SkillExecutionContext


class ValidateGovernanceSkill:
    """Run every registered governance validator and return its full report."""

    def __init__(self, *, validation_pipeline: GovernanceValidationPipeline):
        self._validation_pipeline = validation_pipeline
        self._spec = SkillSpec(
            skill_id="governance.validate_candidate",
            title="Validate Governance Candidate",
            description="Run every enabled deterministic governance constraint against a candidate schema.",
            execution_mode="deterministic",
            side_effect_scope="read_only",
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["partition", "current_schema", "candidate_schema"],
                "properties": {
                    "partition": {"type": "string"},
                    "current_schema": {"type": "object"},
                    "candidate_schema": {"type": "object"},
                    "semantic_key_counts": {"type": "object"},
                    "case_count": {"type": "integer"},
                },
            },
            usage_notes=[
                "Run after drafting the complete candidate_schema and before returning accepted.",
                "Every registered validator runs; do not stop after the first failed validator.",
                "The report contains one complete conclusion per validator plus the aggregate passed field.",
            ],
            argument_binding_hints={
                "partition": "request.partition",
                "current_schema": "input_context.current_facet_schema",
                "semantic_key_counts": "input_context.fit_metrics.semantic_key_counts",
                "case_count": "input_context.fit_metrics.case_count",
            },
            output_schema={
                "type": "object",
                "required": ["passed", "reasons", "plugins"],
            },
        )

    @property
    def spec(self) -> SkillSpec:
        return self._spec

    def execute(self, invocation: SkillInvocation, *, context: SkillExecutionContext | None = None) -> SkillResult:
        started_at = datetime.now(timezone.utc)
        _ = context
        inputs = invocation.inputs
        statistics = {
            "case_count": int(inputs.get("case_count", 0) or 0),
            "case_key_stats": inputs.get("semantic_key_counts", {}),
        }
        report = self._validation_pipeline.validate(
            context=GovernanceValidationContext(
                partition=str(inputs.get("partition", invocation.partition)).strip(),
                statistics=statistics,
                current_schema=inputs.get("current_schema", {}),
                candidate_schema=inputs.get("candidate_schema", {}),
            )
        )
        return SkillResult(
            invocation_id=invocation.invocation_id,
            skill_id=invocation.skill_id,
            ok=True,
            output=report.as_dict(),
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )
