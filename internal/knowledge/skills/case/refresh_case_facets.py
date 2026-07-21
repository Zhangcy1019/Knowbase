"""Case-level skill for recomputing resolved facets under the current partition schema."""

from __future__ import annotations

from datetime import datetime, timezone

from internal.models.skill import SkillInvocation, SkillResult, SkillSpec
from internal.models.skill_context import SkillExecutionContext
from internal.ports import CaseFacetResolutionPort, CaseRepositoryPort, PartitionLookupPort
from internal.utils.logger import get_logger

from .payloads import RefreshCaseFacetsPayload


logger = get_logger("knowbase.skills.case.refresh_case_facets")


class RefreshCaseFacetsSkill:
    """Refresh one case's resolved facets under the current partition schema."""

    def __init__(
        self,
        *,
        case_repository: CaseRepositoryPort,
        partition_service: PartitionLookupPort,
        facet_resolver: CaseFacetResolutionPort,
    ):
        self._case_repository = case_repository
        self._partition_service = partition_service
        self._facet_resolver = facet_resolver
        self._spec = SkillSpec(
            skill_id="case.refresh_case_facets",
            title="Refresh Case Facets",
            description="Recompute resolved stable facets for one case under the current partition schema.",
            execution_mode="deterministic",
            side_effect_scope="single_resource",
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["case_id"],
                "properties": {
                    "case_id": {"type": "string", "description": "Target case id to refresh."},
                    "force": {"type": "boolean", "description": "Force write even when facets are unchanged."},
                },
            },
            examples=[
                {"inputs": {"case_id": "case-123", "force": False}},
            ],
            usage_notes=[
                "Use this skill only when a specific case needs facet recomputation.",
            ],
            argument_binding_hints={
                "case_id": "input_context.case_id",
            },
        )

    @property
    def spec(self) -> SkillSpec:
        return self._spec

    def execute(self, invocation: SkillInvocation, *, context: SkillExecutionContext | None = None) -> SkillResult:
        started_at = datetime.now(timezone.utc)
        execution_context = context or SkillExecutionContext(partition=invocation.partition, metadata={"source": "runtime"})
        try:
            payload = RefreshCaseFacetsPayload.model_validate(
                {
                    "case_id": invocation.inputs.get("case_id", ""),
                    "force": invocation.inputs.get("force", False),
                }
            )
            document = self._case_repository.get(payload.case_id)
            if document is None:
                raise ValueError(f"case not found: {payload.case_id}")

            facet_definitions = self._partition_service.list_facet_definitions(document.partition)
            resolved = self._facet_resolver.project_from_semantic_profile(
                semantic_profile=document.semantic_profile,
                facet_definitions=facet_definitions,
            )
            if not payload.force and resolved == document.facets:
                logger.info("No case facet changes detected for %s", payload.case_id)
                return SkillResult(
                    invocation_id=invocation.invocation_id,
                    skill_id=invocation.skill_id,
                    ok=True,
                    updated_objects=[],
                    output={
                        "updated_objects": [],
                        "reasoning_summary": f"refresh_case_facets skipped for {document.partition}:{payload.case_id}",
                    },
                    started_at=started_at,
                    finished_at=datetime.now(timezone.utc),
                )

            updated = document.model_copy(update={"facets": resolved, "updated_at": datetime.now(timezone.utc)})
            self._case_repository.upsert(updated)
            logger.info("Executing refresh_case_facets for %s:%s", document.partition, payload.case_id)
            return SkillResult(
                invocation_id=invocation.invocation_id,
                skill_id=invocation.skill_id,
                ok=True,
                updated_objects=[payload.case_id],
                output={
                    "updated_objects": [payload.case_id],
                    "reasoning_summary": f"refresh_case_facets completed for {document.partition}:{payload.case_id}",
                },
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "refresh_case_facets failed",
                extra={
                    "case_id": invocation.inputs.get("case_id", ""),
                    "partition": execution_context.partition,
                    "error": str(exc),
                },
            )
            return SkillResult(
                invocation_id=invocation.invocation_id,
                skill_id=invocation.skill_id,
                ok=False,
                updated_objects=[],
                output={},
                error_message=str(exc),
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
            )
