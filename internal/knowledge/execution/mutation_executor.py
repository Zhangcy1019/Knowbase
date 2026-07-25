"""Apply accepted Knowledge mutation plans to domain files without version control."""

from __future__ import annotations

from dataclasses import dataclass, field

from internal.models import CaseFacetProfile


@dataclass(slots=True)
class MutationApplyResult:
    plan_id: str = ""
    updated_case_ids: list[str] = field(default_factory=list)
    updated_paths: list[str] = field(default_factory=list)


class KnowledgeMutationExecutor:
    """Apply an accepted mutation plan; commit and rollback belong to versioning."""

    def __init__(self, *, case_repository, partition_service=None):
        self._case_repository = case_repository
        self._partition_service = partition_service

    def apply(self, *, plan) -> MutationApplyResult:
        if not plan.plan_id:
            raise ValueError("mutation plan requires plan_id")
        if not plan.partition:
            raise ValueError("mutation plan requires partition")
        self._validate_plan(plan=plan)
        updated_case_ids: list[str] = []
        updated_paths: list[str] = []
        if plan.accepted_schema is not None:
            self._partition_service.save_facet_schema(
                partition_name=plan.partition,
                facet_schema=plan.accepted_schema,
            )
            updated_paths.append(f"partition_facet_schemas/{plan.partition}.json")
        for change in plan.case_changes:
            case = self._case_repository.get(change.case_id)
            assert case is not None
            self._case_repository.upsert(
                case.model_copy(
                    update={"facets": CaseFacetProfile.model_validate(change.after_facets)}
                )
            )
            updated_case_ids.append(case.case_id)
            updated_paths.append(f"cases/{case.case_id}.json")
        return MutationApplyResult(
            plan_id=plan.plan_id,
            updated_case_ids=updated_case_ids,
            updated_paths=sorted(set(updated_paths)),
        )

    @staticmethod
    def planned_paths(*, plan) -> list[str]:
        """Return all workspace paths that a plan may mutate for transaction rollback."""
        paths = [f"cases/{change.case_id}.json" for change in plan.case_changes]
        if plan.accepted_schema is not None:
            paths.append(f"partition_facet_schemas/{plan.partition}.json")
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
