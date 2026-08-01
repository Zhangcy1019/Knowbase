"""Apply accepted Knowledge mutation plans to domain files without version control."""

from __future__ import annotations

from dataclasses import dataclass, field

from internal.knowledge.statistics import CaseObservation
from internal.models import CaseFacetProfile


@dataclass(slots=True)
class MutationApplyResult:
    plan_id: str = ""
    updated_case_ids: list[str] = field(default_factory=list)
    updated_paths: list[str] = field(default_factory=list)


class KnowledgeMutationExecutor:
    """Apply an accepted mutation plan; commit and rollback belong to versioning."""

    def __init__(self, *, case_repository, partition_service=None, statistics=None):
        self._case_repository = case_repository
        self._partition_service = partition_service
        self._statistics = statistics

    def apply(self, *, plan) -> MutationApplyResult:
        if not plan.plan_id:
            raise ValueError("mutation plan requires plan_id")
        if not plan.partition:
            raise ValueError("mutation plan requires partition")
        self._validate_plan(plan=plan)
        updated_case_ids: list[str] = []
        updated_paths: list[str] = []
        observation_replacements: list[tuple[CaseObservation, CaseObservation]] = []
        if plan.accepted_schema is not None:
            self._partition_service.save_facet_schema(
                partition_name=plan.partition,
                facet_schema=plan.accepted_schema,
            )
            updated_paths.append("facet_schema.json")
        for change in plan.case_changes:
            case = self._case_repository.get(change.case_id)
            assert case is not None
            updated_case = case.model_copy(
                update={"facets": CaseFacetProfile.model_validate(change.after_facets)}
            )
            if self._statistics is not None:
                observation_replacements.append(
                    (
                        self._observation(case),
                        self._observation(updated_case),
                    )
                )
            self._case_repository.upsert(updated_case)
            updated_case_ids.append(case.case_id)
            updated_paths.append(f"cases/{case.case_id}.json")
        self._refresh_derived_state(
            partition=plan.partition,
            observation_replacements=observation_replacements,
        )
        return MutationApplyResult(
            plan_id=plan.plan_id,
            updated_case_ids=updated_case_ids,
            updated_paths=sorted(set(updated_paths)),
        )

    def _refresh_derived_state(
        self,
        *,
        partition: str,
        observation_replacements: list[tuple[CaseObservation, CaseObservation]],
    ) -> None:
        """Synchronize indexes and changed observations after applying projections."""
        case_documents = self._case_repository.list_by_partition(partition)
        if self._partition_service is not None and hasattr(self._partition_service, "refresh_facet_index"):
            self._partition_service.refresh_facet_index(
                partition_name=partition,
                case_documents=case_documents,
            )
        if self._partition_service is not None and hasattr(self._partition_service, "refresh_semantic_index"):
            self._partition_service.refresh_semantic_index(
                partition_name=partition,
                case_documents=case_documents,
            )
        if self._statistics is not None:
            for old_observation, new_observation in observation_replacements:
                self._statistics.replace_case_observation(
                    old_observation=old_observation,
                    new_observation=new_observation,
                )

    @staticmethod
    def _observation(document) -> CaseObservation:
        return CaseObservation(
            observation_id=f"case:{document.case_id}",
            partition=document.partition,
            source_id=document.case_id,
            facets=document.facets.model_dump(),
            semantic_profile=document.semantic_profile.model_dump(),
        )

    @staticmethod
    def planned_paths(*, plan) -> list[str]:
        """Return all workspace paths that a plan may mutate for transaction rollback."""
        paths = [f"cases/{change.case_id}.json" for change in plan.case_changes]
        paths.extend(["facet_index.json", "semantic_index.json"])
        if plan.accepted_schema is not None:
            paths.append("facet_schema.json")
        return sorted(set(paths))

    def _validate_plan(self, *, plan) -> None:
        if plan.accepted_schema is not None and self._partition_service is None:
            raise RuntimeError("partition_service is required to apply a schema mutation")
        for change in plan.case_changes:
            case = self._case_repository.get(change.case_id)
            if case is None:
                raise ValueError(f"case not found while applying mutation plan: {change.case_id}")
            if case.partition != plan.partition or change.partition != plan.partition:
                raise ValueError(f"case partition does not match mutation plan: {change.case_id}")
            if case.facets.model_dump() != change.before_facets:
                raise ValueError(f"case facets changed since mutation planning: {change.case_id}")

__all__ = ["KnowledgeMutationExecutor", "MutationApplyResult"]
