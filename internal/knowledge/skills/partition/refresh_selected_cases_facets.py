"""Partition-level skill for refreshing facets across a selected case set."""

from __future__ import annotations

from datetime import datetime, timezone

from internal.models.skill import SkillInvocation, SkillResult, SkillSpec
from internal.models.skill_context import SkillExecutionContext
from internal.ports import CaseFacetResolutionPort, CaseRepositoryPort, PartitionAccessPort
from internal.utils.logger import get_logger


logger = get_logger("knowbase.skills.partition.refresh_selected_cases_facets")


class RefreshSelectedCasesFacetsSkill:
    """Recompute resolved facets for a set of cases inside one partition."""

    def __init__(
        self,
        *,
        case_repository: CaseRepositoryPort,
        partition_service: PartitionAccessPort,
        facet_resolver: CaseFacetResolutionPort,
    ):
        self._case_repository = case_repository
        self._partition_service = partition_service
        self._facet_resolver = facet_resolver
        self._spec = SkillSpec(
            skill_id="partition.refresh_selected_cases_facets",
            title="Refresh Selected Cases Facets",
            description="Recompute resolved facets for selected cases under the current partition schema.",
            execution_mode="agent",
            side_effect_scope="partition",
            tags=["partition", "facet", "refresh", "governance"],
        )

    @property
    def spec(self) -> SkillSpec:
        return self._spec

    def execute(self, invocation: SkillInvocation, *, context: SkillExecutionContext | None = None) -> SkillResult:
        started_at = datetime.now(timezone.utc)
        _ = context
        partition = str(invocation.inputs.get("partition", "")).strip()
        case_ids = [str(item).strip() for item in invocation.inputs.get("case_ids", []) if str(item).strip()]
        updated_objects: list[str] = []
        changed_case_ids: list[str] = []
        unchanged_case_ids: list[str] = []
        facet_definitions = self._partition_service.list_facet_definitions(partition)
        for case_id in case_ids:
            document = self._case_repository.get(case_id)
            if document is None or document.partition != partition:
                continue
            next_facets = self._facet_resolver.project_from_semantic_profile(
                semantic_profile=document.semantic_profile,
                facet_definitions=facet_definitions,
            )
            if next_facets == document.facets:
                unchanged_case_ids.append(case_id)
                continue
            updated = document.model_copy(
                update={
                    "facets": next_facets,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            self._case_repository.upsert(updated)
            updated_objects.append(case_id)
            changed_case_ids.append(case_id)
        partition_cases = self._case_repository.list_by_partition(partition) if partition else []
        self._partition_service.refresh_facet_index(
            partition_name=partition,
            case_documents=partition_cases,
        )
        logger.info(
            "Executed partition-level facet refresh.",
            extra={
                "partition": partition,
                "requested_case_count": len(case_ids),
                "changed_case_count": len(changed_case_ids),
                "unchanged_case_count": len(unchanged_case_ids),
                "partition_case_count": len(partition_cases),
            },
        )
        return SkillResult(
            invocation_id=invocation.invocation_id,
            skill_id=invocation.skill_id,
            ok=True,
            updated_objects=updated_objects,
            output={
                "partition": partition,
                "requested_case_ids": case_ids,
                "changed_case_ids": changed_case_ids,
                "unchanged_case_ids": unchanged_case_ids,
                "partition_case_count": len(partition_cases),
                "reasoning_summary": f"refresh_selected_cases_facets completed for {partition}",
            },
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )
